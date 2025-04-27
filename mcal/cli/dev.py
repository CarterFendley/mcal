import os
import re
import subprocess
import sys
from contextlib import ExitStack
from datetime import datetime
from typing import List
from uuid import uuid4

import click

from mcal.dev import (
    APPLIES,
    DevCluster,
    DummyMount,
    get_cluster,
    list_clusters,
    which_cluster,
)
from mcal.new_relic import client_from_env_file
from mcal.utils.cmd import run_cmd
from mcal.utils.logging import get_logger
from mcal.utils.nr import timestamp_to_datetime

from .util import parse_extra_kwargs

logger = get_logger(__name__, cli=True)

@click.group
def dev():
    pass

@dev.group
def cluster():
    pass

@cluster.command(context_settings={
    'ignore_unknown_options': True,
    'allow_extra_args': True,
})
@click.pass_context
@click.option("--allow-multiple", is_flag=True, help="Allow spawning of multiple clusters")
def create(ctx, allow_multiple: bool = False):

    cluster = get_cluster()
    if not allow_multiple and cluster is not None:
        logger.warning("Existing cluster found and '--allow-multiple' not set, returning pre-existing cluster name.")
        print(cluster.name)
        sys.exit(0)


    cluster_name = f'mcal-dev-{uuid4()}'
    cluster = DevCluster(
        name=cluster_name,
        create=True,
        release_on_del=False, # CLI clusters outlive CLI execution
        created_from='cli',
        create_args=ctx.args
    )

    logger.info("Cluster created!")
    print(cluster.name)

@cluster.command
def setup():
    cluster = get_cluster()
    if cluster is None:
        logger.error("Unable to find existing cluster!")
        sys.exit(1)

    with cluster.shared_data as d:
        config_path = d.config_path()

    logger.info("Usage: $(mcal dev cluster setup)")
    print(f'export KUBECONFIG={config_path}')

@cluster.command
def delete_all():
    clusters = list_clusters()
    for cluster in clusters:
        cluster._delete()

    if len(clusters) == 0:
        logger.info("No clusters to delete!")
    else:
        logger.info("All clusters deleted!")


@cluster.command('list')
def dev_cluster_list():
    for cluster in list_clusters():
        print(cluster.name)

@dev.command
@click.option('--env-file', help="Path to environment file")
def nr_list_clusters(env_file: str):
    nr = client_from_env_file(env_file)

    logger.info("Querying NR kubernetes sources...")
    clusters = nr.query(
        """
        FROM K8sClusterSample SELECT latest(timestamp)
        FACET clusterName
        """ 
    )

    if len(clusters) == 0:
        logger.info("No live clusters found connect to NR account")
    else:
        logger.info("Found the following K8 clusters:")

    now = datetime.now()
    for cluster in clusters:
        latest_report = timestamp_to_datetime(cluster['latest.timestamp'])
        last_seen = (now-latest_report).total_seconds()
        print(f"\t'{cluster['clusterName']}' last seen: {last_seen}s")

@cluster.command(context_settings={
    'ignore_unknown_options': True,
    'allow_extra_args': True,
})
@click.pass_context
@click.argument('name')
def apply(ctx, name: str):
    a = APPLIES.get(name)
    if a is None:
        logger.error("No supported apply named '%s'" % name)
        sys.exit(1)
    a = a()

    cluster_name = which_cluster()
    if cluster_name is None:
        logger.error("No cluster found, please use the 'setup' / 'create' tool first")
        sys.exit(1)

    cluster = get_cluster(cluster_name)
    if cluster is None:
        logger.error("Cluster defined by 'KUBECONFIG' can no longer be found.")
        sys.exit(1)

    kwargs = parse_extra_kwargs(ctx)
    with cluster.shared_data as d: # TODO: Don't grab the lock this whole time, these operations run for a while
        try:
            new_labels = a.apply(d.name, **kwargs)
        except Exception as err:
            logger.error("Apply failed: %s" % err)
            sys.exit(1)

        if new_labels is not None:
            for label in new_labels:
                d.labels.add(label)

@dev.group
def pod():
    pass

@pod.command
@click.argument('pod_name')
@click.option('--shell', default='/bin/bash')
def shell(pod_name: str, shell: str):
    if not shell.startswith("/"):
        shell = f"/bin/{shell}"

    args=[
            'kubectl', 'exec', '--stdin', '--tty', pod_name,
            '--', shell
        ]
    print(' '.join(args))
    run_cmd(
        args=[
            'kubectl', 'exec', '--stdin', '--tty', pod_name,
            '--', shell
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE
    )



@dev.group
def pvc():
    pass

def parse_path(path: str):
    if ':' not in path:
        return {'type': 'local', 'path': path}

    prefix, path = path.split(':', 1)
    if prefix == "":
        logger.error(f"Invalid format, empty prefix.")
        sys.exit(1)

    # Filter out empty strings between slashes (e.g. "pod//name" or "pod/name/")
    parts = [p for p in prefix.split('/') if p != ""]

    if not parts:
        logger.error(f"Invalid path format - prefix contains only slashes: {path}") 
        sys.exit(1)

    if len(parts) == 2:
        return {
            'type': parts[0],
            'namespace': None,
            'name': parts[1],
            'path': path
        }
    elif len(parts) == 3:
        return {
            'type': parts[0],
            'namespace': parts[1],
            'name': parts[2],
            'path': path
        }
    else:
        logger.error(f"Invalid path format: {path}")
        sys.exit(1)

# LSP issues
# 1. Step into function
# 3. Highlighting differences
# 4. Suggestions highligted same as comments
# 5. No hover information

def prepare_path(path: str, stack: ExitStack) -> str:
    """Prepare a path for kubectl cp, returns formatted path with namespace if needed"""
    path_info = parse_path(path)

    if path_info['type'] == 'local':
        return path_info['path']
    elif path_info['type'] == 'pvc':
        logger.info(f"Creaing dummy mount for PVC '{path_info['name']}' in namespace '{path_info['namespace']}'...")
        mount = stack.enter_context(DummyMount(path_info['name']))
        logger.info(f"Dummy pod '{mount.pod_name}' created and ready!")

        pod_name = mount.pod_name
        # Join with pvc mount point and normalize
        path = os.path.abspath(os.path.join('/pvc-vol', path_info['path']))
        # Verify path is within pvc-vol directory
        if not path.startswith('/pvc-vol'):
            logger.error(f"Path {path} is outside PVC mount point")
            sys.exit(1)
    elif path_info['type'] == 'pod':
        pod_name = path_info['name']
        path = path_info['path']
    else:
        logger.error(f"Unknown path type: {path_info['type']}")
        sys.exit(1)

    return f"{pod_name}:{path}"

@pvc.command('cp')
@click.argument('src')
@click.argument('dst')
def cp(src: str, dst: str):
    """Copy files between local files, pods, and PVCs.

    Format for pod/pvc paths:
    - pod/<namespace>/<pod_name>:/path/in/pod
    - pod/<pod_name>:/path/in/pod
    - pvc/<namespace>/<pvc_name>:/path/in/pvc
    - pvc/<pvc_name>:/path/in/pvc
    """
    with ExitStack() as stack:
        prepared_src = prepare_path(src, stack)
        prepared_dst = prepare_path(dst, stack)

        cmd = ['kubectl', 'cp', prepared_src, prepared_dst]

        logger.info(f"Copying files using command: {' '.join(cmd)}")
        try:
            run_cmd(cmd, stdout=subprocess.PIPE)
            logger.info("File copy completed successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to copy files: {e}")
            sys.exit(1)

        logger.info("Shutting down dummy pods...")
        stack.close()


@pvc.command('inspect')
@click.argument('pvc_path')
def inspect(pvc_path: str):
    """Open a shell to inspect contents of a PVC using a temporary pod.

    Format for PVC path:
    - <namespace>/<pvc_name>
    - <pvc_name>

    Creates a temporary pod that mounts the specified PVC and opens an interactive shell,
    allowing you to explore the PVC contents with commands like ls, cat, etc.
    The shell will start in the PVC mount directory (/pvc-vol/).
    """
    # Parse PVC path to get namespace and name
    parts = pvc_path.split('/')
    if len(parts) > 2:
        logger.error("Invalid PVC path format. Use: <namespace>/<pvc_name> or <pvc_name>")
        sys.exit(1)
    
    namespace = parts[0] if len(parts) == 2 else None
    pvc_name = parts[-1]

    with DummyMount(pvc_name, namespace=namespace) as mount:
        logger.info(f"Created temporary pod '{mount.pod_name}' with PVC '{pvc_name}' mounted")
        logger.info("Opening shell to pod. Use 'exit' to quit and cleanup.")

        cmd = ['kubectl', 'exec', '-it']
        if namespace:
            cmd.extend(['-n', namespace])
        cmd.extend([mount.pod_name, '--', '/bin/bash', '-c', 'cd /pvc-vol && /bin/bash'])

        try:
            subprocess.run(cmd)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error while running shell: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            logger.info("\nDetected Ctrl+C, cleaning up...")

        logger.info("Shell session ended, cleaning up temporary pod...")
