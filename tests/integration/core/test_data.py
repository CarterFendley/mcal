import os

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from test_resources.cli_fixtures import CLIRunFixture

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
CONFIG_SCHEMA_CHANGES = os.path.join(THIS_DIR, 'config_schema_changes.yml')

def test_schema_changes(cli_run: CLIRunFixture):
    _, data = cli_run(
        CONFIG_SCHEMA_CHANGES,
        config_arguments={}
    )

    data = data.collected_data['_DummySampler'].raw_data
    data = data.drop(columns=['timestamp', 'id'])

    expected = pd.DataFrame([
        {'0': 0, '1': np.nan, '2': np.nan},
        {'0': np.nan, '1': 1, '2': np.nan},
        {'0': np.nan, '1': np.nan, '2': 2}
    ])

    assert_frame_equal(
        data,
        expected,
    )