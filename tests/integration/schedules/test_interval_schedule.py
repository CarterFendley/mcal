import os
import re
from datetime import timedelta
from typing import List

import pytest
from test_resources.cli_fixtures import CLIRunFixture

from k_calibrate.utils.time import to_timedelta_str

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
CONFIG_INTERVAL = os.path.join(THIS_DIR, 'config_interval.yml')

@pytest.mark.parametrize(
    "interval, amount",
    [
        (timedelta(seconds=0.5), 5),
        (timedelta(seconds=1), 2)
    ]
)
def test_basic(cli_run: CLIRunFixture, interval: timedelta, amount: int):
    _, data = cli_run(
        CONFIG_INTERVAL,
        config_arguments={
            'interval': to_timedelta_str(interval),
            'amount': f'{amount}'
        },
    )

    assert data is not None
    sample_data = data.collected_data

    # Should have 2 columns 5 rows
    assert sample_data['_DummySampler'].shape == (amount, 2)
    timestamp_deltas = sample_data['_DummySampler']['timestamp'].diff()
    timestamp_deltas = timestamp_deltas.iloc[1:] # Drop the first row since it will be NaT

    diff_from_interval = abs(timestamp_deltas - interval)
    assert (diff_from_interval < timedelta(seconds=0.2)).all()


@pytest.mark.parametrize(
    "interval, amount, assert_in_stderr",
    [
        ("-1s", 5, [r".*ERROR - [^\n]* Specified interval is negative.*"]),
        ("not an interval", 5, [r".*ERROR - [^\n]* Unable to parse 'not an interval' as timedelta.*"]),

    ]
)
def test_parameter_validation(
    cli_run: CLIRunFixture,
    interval: str,
    amount: int,
    assert_in_stderr: List[str]
):
    result, data = cli_run(
        CONFIG_INTERVAL,
        config_arguments={
            'interval': interval,
            'amount': f'{amount}'
        },
        run_cmd_kwargs={
            'expected_return_codes': [1],
            'capture_output': True
        }
    )

    assert data is None
    stderr = result.stderr.decode()
    for pattern in assert_in_stderr:
        assert re.search(pattern, stderr) is not None, f"Regex failed:\n\tRegex:{pattern}\n\tstderr: {stderr}"

def test_slow_loop_warning(cli_run: CLIRunFixture):
    result, _ = cli_run(
        CONFIG_INTERVAL,
        config_arguments={
            'interval': '0s',
            'amount': f'2'
        },
        run_cmd_kwargs={
            'capture_output': True
        }
    )

    stderr = result.stderr.decode()
    assert re.search(".*WARNING - [^\n]* Calculated sleep time is not positive, this may indicate the sleep calculation loop is running too slow, returning immediately: [^\n]* seconds.*", stderr) is not None