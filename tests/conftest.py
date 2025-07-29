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

    parser.addoption(
        "--k8",
        action='store_true',
        dest="k8",
        default=False,
        help="Enable k8 tests"
    )

def pytest_configure(config):
    def _add_markexpr(markexpr: str, join_op: str = "and"):
        if config.option.markexpr == '':
            config.option.markexpr += f"({markexpr})"
        else:
            config.option.markexpr += f" {join_op} ({markexpr})"

    if config.option.slow:
        _add_markexpr("not slow or slow")
    else:
        _add_markexpr("not slow")

    if config.option.k8:
        _add_markexpr("not k8 or k8")
    else:
        _add_markexpr("not k8")