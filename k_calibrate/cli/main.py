import sys
from typing import Optional

import click

from k_calibrate import orchestrate
from k_calibrate.calibrate import (
    Sample,
    _load_samplers,
    get_sampler,
)
from k_calibrate.config import load_config_file
from k_calibrate.utils.logging import get_logger, set_cli_level

from .util import parse_extra_kwargs

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

    kwargs = parse_extra_kwargs(ctx)

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

@kc.command(context_settings={
    'ignore_unknown_options': True,
    'allow_extra_args': True,
})
@click.pass_context
@click.argument('config_path')
@click.option('--save-name', help="Name to save the run as in the save folder.")
@click.option('--save-directory', help="Directory to save the run in.")
def run(
    ctx,
    config_path: str,
    save_name: Optional[str] = None,
    save_directory: Optional[str] = None
):
    arguments = parse_extra_kwargs(ctx)
    config = load_config_file(config_path, arguments=arguments)
    orchestrate.run(
        config,
        name=save_name,
        save_directory=save_directory
    )
