import re
import sys
from datetime import datetime
from typing import List
from uuid import uuid4

import click

from mcal.dev import (
    APPLIES,
    DevCluster,
    get_cluster,
    list_clusters,
    which_cluster,
)
from mcal.new_relic import client_from_env_file
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