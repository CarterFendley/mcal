import logging
import time
from datetime import datetime, timedelta

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

import k_calibrate.calibrate
from k_calibrate.calibrate import DETAILED_FORMAT, ReferencedIntervalSchedule
from k_calibrate.utils.time import utc_now

logger_name = k_calibrate.calibrate.__name__

def assert_within(
    t1: datetime,
    t2: datetime,
    within: timedelta = timedelta(seconds=0.1)
):
    assert abs(t1 - t2) <= within

def test_parameters_checks(caplog):
    # Note UTC time
    with pytest.raises(NotImplementedError):
        ReferencedIntervalSchedule(
            interval=timedelta(seconds=5),
            reference_time=datetime.now()
        )

    # Negative
    with pytest.raises(NotImplementedError):
        ReferencedIntervalSchedule(
            interval=timedelta(seconds=-1),
            reference_time=utc_now()
        )

    # Future reference time
    with pytest.raises(NotImplementedError):
        ReferencedIntervalSchedule(
            interval=timedelta(seconds=5),
            reference_time=utc_now() + timedelta(days=1)
        )

    # Old reference time
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger=logger_name):
        ReferencedIntervalSchedule(
            interval=timedelta(seconds=5),
            reference_time=utc_now() - timedelta(hours=1, seconds=1)
        )
    assert (logger_name, logging.WARNING, "Reference timestamp is greater than one hour old.") in caplog.record_tuples

def test_basic():
    schedule = ReferencedIntervalSchedule(
        interval=timedelta(seconds=0.1),
        reference_time=utc_now()
    )

    for i in range(0, 5):
        schedule.sleep()
        assert_within(
            utc_now(),
            schedule.reference_time + ((i+1) * schedule.interval),
        )

@pytest.mark.parametrize(
    "num_missed",
    (1, 2, 3, 4)
)
def test_too_slow_loop(caplog, num_missed: int):
    interval = timedelta(seconds=0.1)
    schedule = ReferencedIntervalSchedule(
        interval=interval,
        reference_time=utc_now()
    )

    schedule.sleep()
    assert len(caplog.record_tuples) == 0

    # Intentionally miss 3 intervals
    time.sleep(
        (
            (schedule.interval * num_missed)
            + interval * 0.5 # Fully miss the interval
        ).total_seconds()
    )
    schedule.sleep()
    assert len(caplog.record_tuples) != 0

    expected_missed = []
    for i in range(num_missed):
        interval_number = i + 2 # One bc zero based range(...) and one bc we already missed one interval
        expected_missed.append(
            schedule.reference_time + ((interval_number) * schedule.interval)
        )
    expected_missed = map(lambda t: t.strftime(DETAILED_FORMAT), expected_missed)
    assert (
        logger_name,
        logging.WARNING,
        "Missed %s targets, this probably indicates your loop is not running fast enough for the associated interval, the following timestamps will have no executions:\n%s" % (num_missed, ("\n".join(expected_missed)))
    ) in caplog.record_tuples

@pytest.mark.slow
@pytest.mark.parametrize(
    "interval, iters",
    [
        (timedelta(seconds=1), 5),
        (timedelta(seconds=5), 3),
        (timedelta(seconds=10), 2)
    ]
)
def test_performance(interval: timedelta, iters: int):
    schedule = ReferencedIntervalSchedule(
        interval=interval,
        reference_time=utc_now()
    )

    for i in range(iters):
        schedule.sleep()
        assert_within(
            utc_now(),
            schedule.reference_time + ((i+1) * schedule.interval),
        )