import logging
import os

from k_calibrate import compare
from k_calibrate.compare import Compare, filter_timestamps
from k_calibrate.orchestrate import load_run

THIS_DIR = os.path.abspath(
    os.path.dirname(__file__)
)
EXAMPLE_RUN = os.path.join(THIS_DIR, 'example_run')

logger_name = compare.__name__

def test_duplicate_timestamp(caplog):
    run = load_run(EXAMPLE_RUN)
    compare = Compare(run)

    # Since multiple pods are scraped every timestamp, there will be MORE unique rows than unique timestamps.
    # This detects this to notify user that they may want to be iterating by some subset of keys (like pod name)
    filter_timestamps(compare.yield_data())
    # Note these unique_timestamps / unique_records are unique to this dataset
    assert (
        logger_name,
        logging.WARNING,
        "Number of unique timestamps does not equal the number of unique records, this may indicate that the timestamp is not full indicative of all data collection periods. (dataset=NRTop, unique_timestamps=8, unique_records=102)"
    ) in caplog.record_tuples
    assert (
        logger_name,
        logging.WARNING,
        "Number of unique timestamps does not equal the number of unique records, this may indicate that the timestamp is not full indicative of all data collection periods. (dataset=KubectlTop, unique_timestamps=15, unique_records=270)"
    ) in caplog.record_tuples

    # Now if we filter by podName, this should go away
    caplog.clear()
    compare = Compare(run, iterate_by=['podName'])
    filter_timestamps(compare.yield_data())
    assert (
        logger_name,
        logging.WARNING,
        "Number of unique timestamps does not equal the number of unique records, this may indicate that the timestamp is not full indicative of all data collection periods. (dataset=NRTop, unique_timestamps=8, unique_records=102)"
    ) not in caplog.record_tuples
    assert (
        logger_name,
        logging.WARNING,
        "Number of unique timestamps does not equal the number of unique records, this may indicate that the timestamp is not full indicative of all data collection periods. (dataset=KubectlTop, unique_timestamps=15, unique_records=270)"
    ) not in caplog.record_tuples
