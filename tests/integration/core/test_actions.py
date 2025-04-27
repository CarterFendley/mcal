import os
from pathlib import Path

import pandas as pd
from test_resources.cli_fixtures import CLIRunFixture

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
CONFIG_ONE_ACTION = os.path.join(THIS_DIR, 'config_one_action.yml')
CONFIG_TWO_ACTIONS = os.path.join(THIS_DIR, 'config_two_actions.yml')

def test_one_file_creator(cli_run: CLIRunFixture, tmpdir: Path):
    _, data = cli_run(
        CONFIG_ONE_ACTION,
        config_arguments={
            'interval': '0.1s',
            'directory': str(tmpdir),
            'amount': '4'
        }
    )

    count_data = data.collected_data['_DummyFileCount'].data
    assert count_data['file_count'].equals(pd.Series([0, 1, 2, 3]))

def test_two_file_creators(cli_run: CLIRunFixture, tmpdir: Path):
    _, data = cli_run(
        CONFIG_TWO_ACTIONS,
        config_arguments={
            'interval': '0.1s',
            'directory': str(tmpdir),
            'amount': '4'
        }
    )

    count_data = data.collected_data['_DummyFileCount'].data
    assert count_data['file_count'].equals(pd.Series([0, 2, 4, 6]))