import os

import pytest
from test_resources.cli_fixtures import CLIRunFixture

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
CONFIG_AFTER_ITERATIONS= os.path.join(THIS_DIR, 'config_iterations.yml')

@pytest.mark.parametrize("amount", (1, 2, 3, 5, 8))
def test_after_iterations(cli_run: CLIRunFixture, amount: int):
    _, data = cli_run(
        CONFIG_AFTER_ITERATIONS,
        config_arguments={
            'interval': "50ms",
            'amount': f"{amount}"
        },
    )

    assert data is not None
    assert data.sample_data["_DummySampler"].shape == (amount, 2)