import re
import sys
from datetime import datetime

import click

from k_calibrate import orchestrate
from k_calibrate.calibrate import (_LOADED_SAMPLERS, Sample, _load_samplers,
                                   get_sampler)
from k_calibrate.config import load_config_file
from k_calibrate.data import NR_HELM_VALUES_PATH, render_file_to_temp
from k_calibrate.new_relic import client_from_env_file
from k_calibrate.utils.cmd import is_cmd, run_cmd
from k_calibrate.utils.env_file import load_env_file
from k_calibrate.utils.logging import get_logger, set_cli_level

logger = get_logger(__name__, cli=True)

@click.group
@click.option('-v', '--verbose', count=True, help='Enable verbose logging.')
def kc(verbose: int):
    set_cli_level(
        level=verbose,
        extra_modules=[
            "k_calibrate.calibrate",
            "k_calibrate.orchestrate"
        ]
    )

@kc.group
def sampler():
    pass

@sampler.command
def list():
    samplers = _load_samplers()
    logger.info("Available samplers:")
    for s in samplers:
        print(f"\t{s}")

@sampler.command(context_settings={
    'ignore_unknown_options': True,
    'allow_extra_args': True,
})
@click.pass_context
@click.argument("name")
def run(ctx, name: str):
    sampler = get_sampler(name)
    if sampler is None:
        logger.error("Unable to find sampler with name: '%s'" % name)
        sys.exit(1)

    kwargs = {}
    for kv_pair in ctx.args:
        if not re.match(r"--[^=]+=[^=]+", kv_pair):
            logger.error("Extra arg provided which does not follow '--key=value' pattern: '%s'" % kv_pair)
            sys.exit(1)

        # TODO: Type comparison / conversion to needed type?
        key, value = kv_pair[2:].split('=')
        kwargs[key] = value

    logger.debug("Parsed kwargs from user: %s", kwargs)

    logger.info("Constructing sampler with provided args...")
    logger.info("Sampling...")
    sampler = sampler(**kwargs)
    sample = sampler.sample()

    assert isinstance(sample, Sample), f"Sampler returned non-sample type: %s" % type(sample)

    if hasattr(sampler, 'print_data'):
        sampler.print_data(sample.data_points)
    else:
        print(sample.data_points)

@kc.command
@click.argument('config_path')
def run(config_path: str):
    config = load_config_file(config_path, arguments={})
    orchestrate.run(config)

@kc.group
def dev():
    pass

@dev.command
@click.option('--env-file', help="Path to environment file")
def list_clusters(env_file: str):
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
        latest_report = datetime.fromtimestamp(cluster['latest.timestamp'] / 1000.0) # TODO: Bit shift?
        last_seen = (now-latest_report).total_seconds()
        print(f"\t'{cluster['clusterName']}' last seen: {last_seen}s")


@dev.command
@click.argument('cluster-name')
@click.option('--env-file', help="Path to environment file")
def nr_bootstrap(cluster_name: str, env_file: str):
    if env_file is not None:
        env = load_env_file(env_file)
    else:
        env = load_env_file()

    if not is_cmd('kubectl') or not is_cmd('helm'):
        logger.error("Cluster bootstrap requires both 'kubectl' and 'helm' to be installed")
        sys.exit(1)

    logger.info("Rendering helm values...")
    helm_values_path = render_file_to_temp(
        NR_HELM_VALUES_PATH,
        {
            'cluster_name': cluster_name,
            'license_key': env.get_license_key()
        }
    )

    logger.info("Testing cluster connection")
    result = run_cmd(
        ['kubectl', 'cluster-info'],
        expected_return_codes=[0, 1] # Expecting 1 to handle gracefully
    )
    if result.returncode == 1:
        logger.error("Unable to get cluster info via 'kubectl', is the cluster active")
        sys.exit(1)

    logger.info("Adding NR helm repo")
    run_cmd(
        ['helm', 'repo', 'add', 'newrelic', 'https://helm-charts.newrelic.com'],
    )

    helm_args = [
        'helm', 'upgrade', '--install', 'newrelic-bundle', 'newrelic/nri-bundle',
        '--namespace', 'newrelic', '--create-namespace',
        '-f', helm_values_path.name,
        # Validating args
        '--dry-run',
        '--debug'
    ]
    logger.info("Validating helm command...")
    with open(helm_values_path.name, 'r') as f:
        print(f.read())
    run_cmd(
        helm_args
    )


    logger.info("Bootstrapping activate kubetctl context with NR integration, naming cluster '%s'" % cluster_name)
    helm_args.remove('--dry-run')
    helm_args.remove('--debug')
    run_cmd(
        helm_args
    )

    logger.info("Bootstraping complete!")
    logger.info("Note: Services may take a while to spin up, check status with the command below.")
    print('\tkubectl -n newrelic get pods -w')
    # TODO: Preform monitoring here?