from typing import Dict
from unittest.mock import patch

import pandas as pd
from pytest_unordered import unordered

from mcal.compare import Compare
from mcal.config import MCalConfig, ScheduleConfig, StopCriteriaConfig
from mcal.runner.models import CalibrationRun
from mcal.samplers.base import SamplerData
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
def patch_collected_data(run: CalibrationRun):
    # TODO: This is a hack to get tests working from when `collected_data` was changed to contain SamplerData objects (from pd.DataFrames). This was done to facilitate the tracking of `ids` and which `ids` were new. Need to re-examine the use of SamplerData in `collected_data` especially when it comes to saving run data and testing.
    for key, collected_data in run.collected_data.items():
        collected_data['timestamp'] = None # TODO: Check this as well, don't need a timestamp in this testing but `from_dataframe` assumes existence for tracking IDs (usually a good assumption) which is not true in this mocked data case.
        run.collected_data[key] = SamplerData.from_dataframe(
            source_name=key,
            df=collected_data
        )
patch_collected_data(FAKE_RUN)
patch_collected_data(FAKE_RUN_COMPLEX)
patch_collected_data(FAKE_RUN_MULTI_KEY)

def assert_df_dict_eq(d1: Dict[str, pd.DataFrame], d2: Dict[str, pd.DataFrame]):
    assert tuple(d1.keys()) == tuple(d2.keys())

    for key in d1.keys():
        assert d1[key].equals(d2[key])

def test_basic():
    c = Compare(FAKE_RUN)

    yielded = list(c.yield_data())
    assert len(yielded) == 1
    expect = {k:v.data for k,v in FAKE_RUN.collected_data.items()}
    assert_df_dict_eq(yielded[0], expect)

def df_compare(self: pd.DataFrame, other: pd.DataFrame):
    return self.equals(other)

@patch("pandas.DataFrame.__eq__", df_compare)
def test_iterate_by():
    c = Compare(FAKE_RUN, iterate_by=['state'])

    yielded = list(c.yield_data())
    assert len(yielded) == 2
    expected = [
        {
            'estimate_one': FAKE_RUN.collected_data['estimate_one'].data.query('state=="NY"').reset_index(drop=True),
            'estimate_two': FAKE_RUN.collected_data['estimate_two'].data.query('state=="NY"').reset_index(drop=True),
        },
        {
            'estimate_one': FAKE_RUN.collected_data['estimate_one'].data.query('state=="NJ"').reset_index(drop=True),
            'estimate_two': FAKE_RUN.collected_data['estimate_two'].data.query('state=="NJ"').reset_index(drop=True),
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
            'estimate_one': FAKE_RUN_COMPLEX.collected_data['estimate_one'].data.query('state=="NY"').reset_index(drop=True),
            'estimate_two': FAKE_RUN_COMPLEX.collected_data['estimate_two'].data.query('state=="NY"').reset_index(drop=True),
            'estimate_three': FAKE_RUN_COMPLEX.collected_data['estimate_three'].data.query('state=="NY"').reset_index(drop=True),
        },
        {
            'estimate_one': FAKE_RUN_COMPLEX.collected_data['estimate_one'].data.query('state=="NJ"').reset_index(drop=True),
            'estimate_two': FAKE_RUN_COMPLEX.collected_data['estimate_two'].data.query('state=="NJ"').reset_index(drop=True),
            'estimate_three': FAKE_RUN_COMPLEX.collected_data['estimate_three'].data.query('state=="NJ"').reset_index(drop=True),
        },
        {
            'estimate_one': FAKE_RUN_COMPLEX.collected_data['estimate_one'].data.query('state=="GA"').reset_index(drop=True),
            'estimate_two': FAKE_RUN_COMPLEX.collected_data['estimate_two'].data.query('state=="GA"').reset_index(drop=True),
            'estimate_three': FAKE_RUN_COMPLEX.collected_data['estimate_three'].data.query('state=="GA"').reset_index(drop=True),
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
            'estimate_one': FAKE_RUN_MULTI_KEY.collected_data['estimate_one'].data.query('state=="NY" & city=="New York"').reset_index(drop=True),
            'estimate_two': FAKE_RUN_MULTI_KEY.collected_data['estimate_two'].data.query('state=="NY" & city=="New York"').reset_index(drop=True),
        },
        {
            'estimate_one': FAKE_RUN_MULTI_KEY.collected_data['estimate_one'].data.query('state=="NY" & city=="Albany"').reset_index(drop=True),
            'estimate_two': FAKE_RUN_MULTI_KEY.collected_data['estimate_two'].data.query('state=="NY" & city=="Albany"').reset_index(drop=True),
        },
        {
            'estimate_one': FAKE_RUN_MULTI_KEY.collected_data['estimate_one'].data.query('state=="NJ" & city=="Trenton"').reset_index(drop=True),
            'estimate_two': FAKE_RUN_MULTI_KEY.collected_data['estimate_two'].data.query('state=="NJ" & city=="Trenton"').reset_index(drop=True),
        },
    ]
    assert yielded == unordered(expected)