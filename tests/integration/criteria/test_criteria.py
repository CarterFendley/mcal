import os
import subprocess
import time

import pytest
from test_resources.cli_fixtures import CLIRunFixture

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
CONFIG_NO_CRITERIA = os.path.join(THIS_DIR, 'config_no_criteria.yml')
CONFIG_AFTER_ITERATIONS= os.path.join(THIS_DIR, 'config_iterations.yml')

@pytest.mark.parametrize(
    "wait",
    [
        0.5,
        pytest.param(1, marks=pytest.mark.slow),
        pytest.param(2, marks=pytest.mark.slow)
    ]
)
def test_allow_no_criteria(wait: float):
    handle = subprocess.Popen(
        ["mcal", "-vvv", "run", CONFIG_NO_CRITERIA],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line-buffered
    )

    for line in iter(handle.stderr.readline, ''):
        # NOTE: All stderr before the break will be unavailable
        if 'Starting run loop...' in line:
            print("Breaking")
            break

    time.sleep(wait)

    exit_code = handle.poll()
    if exit_code is not None:
        stdout, stderr = handle.communicate()
        print('=========================')
        print(stderr)
        print('-------------------------')
        print(stdout)
        assert exit_code is None, "Process exited without stop_criteria!"


    # Kill the process ourself
    handle.kill()


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
    assert data.collected_data["_DummySampler"].shape == (amount, 2)