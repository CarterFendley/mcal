import asyncio
import sys
from typing import Optional

import click
import pandas as pd

from mcal.calibrate import (
    _load_samplers,
    get_sampler,
)
from mcal.config import load_config_file
from mcal.runner import orchestrate
from mcal.utils.logging import get_logger, set_cli_level

from .dev import dev
from .util import parse_extra_kwargs

logger = get_logger(__name__, cli=True)

@click.group
@click.option('-v', '--verbose', count=True, help='Enable verbose logging.')
def mcal(verbose: int):
    set_cli_level(
        level=verbose,
        extra_modules=[
            "mcal.calibrate",
            "mcal.runner.orchestrate"
        ]
    )

mcal.add_command(dev)

@mcal.group
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

    assert isinstance(sample, (pd.Series, pd.DataFrame)), f"Sampler returned non-sample type: %s" % type(sample)

    # TODO: Breakdown the `CalibrateRun` saves so that Sample only data can be saved here
    print(sample)

@mcal.command(context_settings={
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

    run_data = asyncio.run(orchestrate.run(config))

    save_path = run_data.write_run(
        name=save_name,
        save_directory=save_directory,
    )
    logger.info("Wrote run data to path: %s" % save_path)