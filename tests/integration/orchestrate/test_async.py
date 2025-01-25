import os
from datetime import timedelta

import pytest
from test_resources.cli_fixtures import CLIRunFixture

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
CONFIG_TWO_DELAYED = os.path.join(THIS_DIR, 'config_two_delayed.yml')


@pytest.mark.parametrize(
    "delay",
    [
        0.2,
        0.5,
        pytest.param(1, marks=pytest.mark.slow),
        pytest.param(2, marks=pytest.mark.slow)
    ]
)
def test_basic_delay(cli_run: CLIRunFixture, delay: float):
    _, data = cli_run(
        CONFIG_TWO_DELAYED,
        config_arguments={
            'interval': '0.5s',
            'delay': f'{delay}',
            'amount': '1'
        }
    )

    assert data is not None

    dummy_one = data.collected_data['dummy_one']
    dummy_two = data.collected_data['dummy_two']
    assert dummy_one.shape == (1, 2)
    assert dummy_two.shape == (1, 2)

    t1 = dummy_one['timestamp'][0]
    t2 = dummy_two['timestamp'][0]
    assert abs(t1 - t2) < timedelta(seconds=delay)