from test_resources.cli_fixtures import *
from test_resources.fixtures import *


def pytest_addoption(parser):
    # NOTE: This is so you don't have to use the `-m "slow or not slow"` annoying syntax
    parser.addoption(
        "--slow",
        action='store_true',
        dest="slow",
        default=False,
        help="Enable slow tests"
    )

def pytest_configure(config):
    # TODO: Am I removing the ability to add other markers via CLI here?
    if config.option.slow:
        config.option.markexpr = "not slow or slow"
    else:
        config.option.markexpr = "not slow"