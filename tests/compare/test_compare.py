from typing import Dict
from unittest.mock import patch

import pandas as pd
from pytest_unordered import unordered

from mcal.compare import Compare
from mcal.config import MCalConfig, ScheduleConfig, StopCriteriaConfig
from mcal.runner.models import CalibrationRun
from mcal.utils.time import utc_now

FAKE_CONFIG = MCalConfig(
    schedule=ScheduleConfig(
        kind='IntervalSchedule',
        args={'interval': '5s'}
    ),
    samplers=[],
    stop_criteria=StopCriteriaConfig(
        kind='builtin:after_iterations',
        args={'amount': '15'}
    )
)
FAKE_RUN = CalibrationRun(
    start_time=utc_now(),
    config=FAKE_CONFIG,
    collected_data={
        'estimate_one': pd.DataFrame([
            {'year': '0', 'state': 'NY', 'population': '8m'},
            {'year': '0', 'state': 'NJ', 'population': '8.5m'},
            {'year': '1', 'state': 'NY', 'population': '8.2m'},
            {'year': '1', 'state': 'NJ', 'population': '8.7m'},
            {'year': '2', 'state': 'NY', 'population': '8.5m'},
            {'year': '2', 'state': 'NJ', 'population': '9.1m'},
        ]),
        'estimate_two': pd.DataFrame([
            {'year': '0', 'state': 'NY', 'population': '8.1m'},
            {'year': '0', 'state': 'NJ', 'population': '8.6m'},
            {'year': '1', 'state': 'NY', 'population': '8.3m'},
            {'year': '1', 'state': 'NJ', 'population': '8.8m'},
            {'year': '2', 'state': 'NY', 'population': '8.6m'},
            {'year': '2', 'state': 'NJ', 'population': '9.2m'},
        ]),
    }
)
FAKE_RUN_COMPLEX = CalibrationRun(
    start_time=utc_now(),
    config=FAKE_CONFIG,
    collected_data={
        'estimate_one': pd.DataFrame([
            {'year': '0', 'state': 'NY', 'population': '8m'},
            {'year': '0', 'state': 'NJ', 'population': '8.5m'},
            {'year': '1', 'state': 'NY', 'population': '8.2m'},
            {'year': '1', 'state': 'NJ', 'population': '8.7m'},
            {'year': '2', 'state': 'NY', 'population': '8.5m'},
            {'year': '2', 'state': 'NJ', 'population': '9.1m'},
        ]),
        'estimate_two': pd.DataFrame([
            {'year': '0', 'state': 'NY', 'population': '8.1m'},
            {'year': '0', 'state': 'NJ', 'population': '8.6m'},
            {'year': '0', 'state': 'GA', 'population': '10m'}, # Note how GA is not in the first DF
            {'year': '1', 'state': 'NY', 'population': '8.3m'},
            {'year': '1', 'state': 'NJ', 'population': '8.8m'},
            {'year': '1', 'state': 'GA', 'population': '10.6m'},
            {'year': '2', 'state': 'NY', 'population': '8.6m'},
            {'year': '2', 'state': 'NJ', 'population': '9.2m'},
            {'year': '3', 'state': 'GA', 'population': '11m'},
        ]),
        'estimate_three': pd.DataFrame([
            {'year': '0', 'state': 'GA', 'population': '10.1m'}, # Note how GA is not in the first DF
            {'year': '1', 'state': 'GA', 'population': '10.5m'},
            {'year': '3', 'state': 'GA', 'population': '11.1m'},
        ]),
    }
)
FAKE_RUN_MULTI_KEY = CalibrationRun(
    start_time=utc_now(),
    config=FAKE_CONFIG,
    collected_data={
        'estimate_one': pd.DataFrame([
            {'year': '0', 'state': 'NY', 'city': 'New York', 'population': '8m'},
            {'year': '0', 'state': 'NY', 'city': 'Albany', 'population': '100k'},
            {'year': '1', 'state': 'NY', 'city': 'New York', 'population': '8.3m'},
            {'year': '1', 'state': 'NY', 'city': 'Albany', 'population': '101k'},
            {'year': '2', 'state': 'NY', 'city': 'New York', 'population': '8.6m'},
            {'year': '2', 'state': 'NY', 'city': 'Albany', 'population': '102k'},
        ]),
        'estimate_two': pd.DataFrame([
            {'year': '0', 'state': 'NY', 'city': 'New York', 'population': '8.1m'},
            {'year': '0', 'state': 'NY', 'city': 'Albany', 'population': '98k'},
            {'year': '0', 'state': 'NJ', 'city': 'Trenton', 'population': '86k'},
            {'year': '1', 'state': 'NY', 'city': 'New York', 'population': '8.4m'},
            {'year': '1', 'state': 'NY', 'city': 'Albany', 'population': '100k'},
            {'year': '1', 'state': 'NJ', 'city': 'Trenton', 'population': '87k'},
            {'year': '2', 'state': 'NY', 'city': 'New York', 'population': '8.5m'},
            {'year': '2', 'state': 'NY', 'city': 'Albany', 'population': '101k'},
            {'year': '2', 'state': 'NJ', 'city': 'Trenton', 'population': '88k'},
        ]),
    }
)

def assert_df_dict_eq(d1: Dict[str, pd.DataFrame], d2: Dict[str, pd.DataFrame]):
    assert tuple(d1.keys()) == tuple(d2.keys())

    for key in d1.keys():
        assert d1[key].equals(d2[key])

def test_basic():
    c = Compare(FAKE_RUN)

    yielded = list(c.yield_data())
    assert len(yielded) == 1
    assert_df_dict_eq(yielded[0], FAKE_RUN.collected_data)

def df_compare(self: pd.DataFrame, other: pd.DataFrame):
    return self.equals(other)

@patch("pandas.DataFrame.__eq__", df_compare)
def test_iterate_by():
    c = Compare(FAKE_RUN, iterate_by=['state'])

    yielded = list(c.yield_data())
    assert len(yielded) == 2
    expected = [
        {
            'estimate_one': FAKE_RUN.collected_data['estimate_one'].query('state=="NY"').reset_index(drop=True),
            'estimate_two': FAKE_RUN.collected_data['estimate_two'].query('state=="NY"').reset_index(drop=True),
        },
        {
            'estimate_one': FAKE_RUN.collected_data['estimate_one'].query('state=="NJ"').reset_index(drop=True),
            'estimate_two': FAKE_RUN.collected_data['estimate_two'].query('state=="NJ"').reset_index(drop=True),
        },
    ]
    assert yielded == unordered(expected)

@patch("pandas.DataFrame.__eq__", df_compare)
def test_iterate_by_complex():
    c = Compare(FAKE_RUN_COMPLEX, iterate_by=['state'])

    yielded = list(c.yield_data())
    assert len(yielded) == 3
    expected = [
        {
            'estimate_one': FAKE_RUN_COMPLEX.collected_data['estimate_one'].query('state=="NY"').reset_index(drop=True),
            'estimate_two': FAKE_RUN_COMPLEX.collected_data['estimate_two'].query('state=="NY"').reset_index(drop=True),
            'estimate_three': FAKE_RUN_COMPLEX.collected_data['estimate_three'].query('state=="NY"').reset_index(drop=True),
        },
        {
            'estimate_one': FAKE_RUN_COMPLEX.collected_data['estimate_one'].query('state=="NJ"').reset_index(drop=True),
            'estimate_two': FAKE_RUN_COMPLEX.collected_data['estimate_two'].query('state=="NJ"').reset_index(drop=True),
            'estimate_three': FAKE_RUN_COMPLEX.collected_data['estimate_three'].query('state=="NJ"').reset_index(drop=True),
        },
        {
            'estimate_one': FAKE_RUN_COMPLEX.collected_data['estimate_one'].query('state=="GA"').reset_index(drop=True),
            'estimate_two': FAKE_RUN_COMPLEX.collected_data['estimate_two'].query('state=="GA"').reset_index(drop=True),
            'estimate_three': FAKE_RUN_COMPLEX.collected_data['estimate_three'].query('state=="GA"').reset_index(drop=True),
        },
    ]
    assert yielded == unordered(expected)

@patch("pandas.DataFrame.__eq__", df_compare)
def test_iterate_by_multi_key():
    c = Compare(FAKE_RUN_MULTI_KEY, iterate_by=['state', 'city'])

    yielded = list(c.yield_data())
    assert len(yielded) == 3
    expected = [
        {
            'estimate_one': FAKE_RUN_MULTI_KEY.collected_data['estimate_one'].query('state=="NY" & city=="New York"').reset_index(drop=True),
            'estimate_two': FAKE_RUN_MULTI_KEY.collected_data['estimate_two'].query('state=="NY" & city=="New York"').reset_index(drop=True),
        },
        {
            'estimate_one': FAKE_RUN_MULTI_KEY.collected_data['estimate_one'].query('state=="NY" & city=="Albany"').reset_index(drop=True),
            'estimate_two': FAKE_RUN_MULTI_KEY.collected_data['estimate_two'].query('state=="NY" & city=="Albany"').reset_index(drop=True),
        },
        {
            'estimate_one': FAKE_RUN_MULTI_KEY.collected_data['estimate_one'].query('state=="NJ" & city=="Trenton"').reset_index(drop=True),
            'estimate_two': FAKE_RUN_MULTI_KEY.collected_data['estimate_two'].query('state=="NJ" & city=="Trenton"').reset_index(drop=True),
        },
    ]
    assert yielded == unordered(expected)