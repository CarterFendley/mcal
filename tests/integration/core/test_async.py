import os
from datetime import timedelta

import pytest
from test_resources.cli_fixtures import CLIRunFixture

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
CONFIG_ONE_ACTION_NO_AWAIT = os.path.join(THIS_DIR, 'config_one_action_no_await.yml')
CONFIG_TWO_DELAYED_SAMPLES = os.path.join(THIS_DIR, 'config_two_delayed_samples.yml')
CONFIG_TWO_DELAYED_ACTIONS = os.path.join(THIS_DIR, 'config_two_delayed_actions.yml')


@pytest.mark.parametrize(
    "delay",
    [
        0.2,
        0.5,
        pytest.param(1, marks=pytest.mark.slow),
        pytest.param(2, marks=pytest.mark.slow)
    ]
)
def test_sampler_delay(cli_run: CLIRunFixture, delay: float):
    _, data = cli_run(
        CONFIG_TWO_DELAYED_SAMPLES,
        config_arguments={
            'interval': '0.5s',
            'delay': f'{delay}',
            'amount': '1'
        }
    )

    assert data is not None

    dummy_one = data.collected_data['dummy_one'].data
    dummy_two = data.collected_data['dummy_two'].data
    assert dummy_one.shape == (1, 2)
    assert dummy_two.shape == (1, 2)

    t1 = dummy_one['timestamp'][0]
    t2 = dummy_two['timestamp'][0]
    assert abs(t1 - t2) < timedelta(seconds=delay)

@pytest.mark.parametrize(
    "delay",
    [
        0.3,
        0.5,
        pytest.param(1, marks=pytest.mark.slow),
        pytest.param(2, marks=pytest.mark.slow)
    ]
)
def test_action_delay(cli_run: CLIRunFixture, delay: float):
    _, data = cli_run(
        CONFIG_TWO_DELAYED_ACTIONS,
        config_arguments={
            # NOTE: Intentionally testing interval of zero to only measure time difference of the actions
            # TODO: Should I implement a continuous schedule?
            'interval': '0s', 
            'delay': f'{delay}',
            'amount': '2'
        }
    )

    timestamps = data.collected_data['_DummySampler'].data['timestamp']

    # Check that we have approximately one delayed interval, not two sequential ones
    assert abs(timestamps.diff()[1] - timedelta(seconds=delay)) < timedelta(seconds=0.2)

@pytest.mark.parametrize(
    "delay",
    [
        0.3,
        0.5,
        pytest.param(1, marks=pytest.mark.slow),
        pytest.param(2, marks=pytest.mark.slow)
    ]
)
def test_action_no_await(cli_run: CLIRunFixture, delay: float):
    _, data = cli_run(
        CONFIG_ONE_ACTION_NO_AWAIT,
        config_arguments={
            # NOTE: Intentionally testing interval of zero to only measure time difference of the actions
            # TODO: Should I implement a continuous schedule?
            'interval': '0s', 
            'delay': f'{delay}',
            'amount': '2'
        }
    )
    timestamps = data.collected_data['_DummySampler'].data['timestamp']

    # Check that the delay does not show up, as the runner should not await it
    assert abs(timestamps.diff()[1]) < timedelta(seconds=0.2)