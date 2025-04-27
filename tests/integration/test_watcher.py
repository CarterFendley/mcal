import os
import re
from typing import Dict

import pytest
from test_resources.cli_fixtures import CLIRunFixture

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
CONFIG_DUMMY_WATCHER = os.path.join(THIS_DIR, 'config_dummy_watcher.yml')
CONFIG_WATCHER_SHORT_TIMEOUT = os.path.join(THIS_DIR, 'config_watcher_short_timeout.yml')
CONFIG_WATCHER_ODD_EVEN = os.path.join(THIS_DIR, 'config_watcher_odd_even.yml')
CONFIG_WATCHER_ORDERED = os.path.join(THIS_DIR, 'config_watcher_ordered.yml')

# Ids that were previously gone only return once
# Test async

def test_watcher(cli_run: CLIRunFixture):
    result, _ = cli_run(
        CONFIG_DUMMY_WATCHER,
        config_arguments={},
        run_cmd_kwargs={
            'capture_output': True
        }
    )

    stdout = result.stdout.decode()
    for i in range(5):
        assert re.search(fr"id found: {i}\n", stdout) is not None, f"Regex failed: {stdout}"

        assert re.search(fr"id found: {i}\n", stdout) is not None,f"Regex failed: {stdout}"

    assert re.search("id gone: ", stdout) is None, f"Unexpected id timeout: {stdout}"

def test_watch_id_timeouts(cli_run: CLIRunFixture):
    result, _ = cli_run(
        CONFIG_WATCHER_SHORT_TIMEOUT,
        config_arguments={},
        run_cmd_kwargs={
            'capture_output': True
        }
    )

    stdout = result.stdout.decode()
    for i in range(5):
        matches = re.findall(fr"id gone: {i}", stdout)
        assert len(matches) == 1, f"Regex failed: {stdout}"

@pytest.mark.parametrize(
    "interval, timeout, value_type, amount, expected_statements",
    [
        (
            "0.15s", "0.20s", "sample_num", 6, {
                # With a timeout longer than the interval, a 'odd' between 'even' will not cause the 'even' to timeout, and vice versa
                "id found: odd": 1,
                "id found: even": 1,
                "id gone: odd": 0,
                "id gone: even": 0,
                "id returned: even": 0,
                "id returned: odd": 0,
                "id updated: even": 3,
                "id updated: odd": 3
            }
        ),
        (
            "0.20s", "0.15s", "sample_num", 6, {
                # With a timeout shorter than the interval, the 'even' ids will be lost after each 'odd' (and vice versa). 'even' and 'odd' will return 2 times and one times respectively.
                # See below:
                # 0 - even -
                # 1 - odd  - lost 'even'
                # 2 - even - lost 'odd' & 'even' returned
                # 3 - odd  - lost 'even' & 'odd' returned
                # 4 - even - lost 'odd' & 'even' returned
                # 5 - odd  - lost 'even' & 'odd' returned
                # Don't @ me for 0 being even.
                "id found: odd": 1,
                "id found: even": 1,
                "id gone: odd": 2,
                "id gone: even": 3,
                "id returned: even": 2,
                "id returned: odd": 2,
                "id updated: even": 3,
                "id updated: odd": 3
            }
        ),
        (
            # NOTE: The change to "numbers_repeated" below
            "0.20s", "0.15s", "numbers_repeated", 12, {
                # This is functionally the same as the test above, just testing that there are no unexpected duplicates for ids being returned or lost.
                "id found: odd": 1,
                "id found: even": 1,
                "id gone: odd": 2,
                "id gone: even": 3,
                "id returned: even": 2,
                "id returned: odd": 2,
                # NOTE: These happen every iteration
                "id updated: even": 6,
                "id updated: odd": 6
            }
        )
    ]
)
def test_watch_odd_even(
    cli_run: CLIRunFixture,
    interval: str,
    timeout: str,
    value_type: str,
    amount: int,
    expected_statements: Dict[str, int]
):
    result, _ = cli_run(
        CONFIG_WATCHER_ODD_EVEN,
        config_arguments={
            'interval': interval,
            'timeout': timeout,
            'value_type': value_type,
            'amount': f"{amount}",
        },
        run_cmd_kwargs={
            'capture_output': True
        }
    )

    stdout = result.stdout.decode()

    # Ids should only be found once (assuming amount > 2)
    for i in ('odd', 'even'):
        matches = re.findall(fr"id found: {i}", stdout)
        assert len(matches) == 1, f"Regex failed: {stdout}"

    for statement, count in expected_statements.items():
        matches = re.findall(statement, stdout)
        assert len(matches) == count, f"Regex '{statement}' failed: {stdout}"

@pytest.mark.parametrize(
    "delay",
    (
        0.2,
        0.5,
        pytest.param(1, marks=pytest.mark.slow),
        pytest.param(2, marks=pytest.mark.slow),
        pytest.param(3, marks=pytest.mark.slow)
    )
)
def test_defined_order(cli_run: CLIRunFixture, delay: float):
    result, _ = cli_run(
        CONFIG_WATCHER_ORDERED,
        config_arguments={
            'delay': f"{delay}"
        },
        run_cmd_kwargs={
            'capture_output': True
        }
    )
    stdout = result.stdout.decode()

    # Note only testing even here b/c after three cycles that is the only id to go through found / gone / returned
    matches = list(re.finditer(r"id found: even", stdout))
    assert len(matches) == 1
    found_match = matches[0]

    matches = list(re.finditer(r"id returned: even", stdout))
    assert len(matches) == 1
    returned_match = matches[0]

    print(type(returned_match))
    print(returned_match)

    matches = list(re.finditer(f"id updated: even", stdout))
    assert len(matches) == 2

    # Assure that found / returned methods are ALWAYS called before update methods
    assert found_match.end() < matches[0].start(), "Out of order call to found made"
    assert returned_match.end() < matches[1].start(), "Out of order call to return made"