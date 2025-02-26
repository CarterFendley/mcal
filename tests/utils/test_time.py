import re
from datetime import timedelta

import pytest

from mcal.utils.time import (
    _UNABLE_TO_PARSE_MESSAGE,
    parse_timedelta,
    to_timedelta_str,
)


@pytest.mark.parametrize(
    "input, expected",
    [
        # Microseconds
        ("0.5us", timedelta(microseconds=0.5)),
        ("1us", timedelta(microseconds=1)),
        ("5us", timedelta(microseconds=5)),
        ("30us", timedelta(microseconds=30)),
        ("500.0us", timedelta(microseconds=500.0)),
        # Milliseconds
        ("0.5ms", timedelta(milliseconds=0.5)),
        ("1ms", timedelta(milliseconds=1)),
        ("5ms", timedelta(milliseconds=5)),
        ("30ms", timedelta(milliseconds=30)),
        ("500.0ms", timedelta(milliseconds=500.0)),
        # Seconds
        ("0.5s", timedelta(seconds=0.5)),
        ("1s", timedelta(seconds=1)),
        ("5s", timedelta(seconds=5)),
        ("30s", timedelta(seconds=30)),
        ("500.0s", timedelta(seconds=500)),
        # Minutes
        ("0.5m", timedelta(minutes=0.5)),
        ("1m", timedelta(minutes=1)),
        ("5m", timedelta(minutes=5)),
        ("30m", timedelta(minutes=30)),
        ("500.0m", timedelta(minutes=500)),
        # Hours
        ("0.5h", timedelta(hours=0.5)),
        ("1h", timedelta(hours=1)),
        ("5h", timedelta(hours=5)),
        ("30h", timedelta(hours=30)),
        ("500.0h", timedelta(hours=500)),
        # Days
        ("0.5d", timedelta(days=0.5)),
        ("1d", timedelta(days=1)),
        ("5d", timedelta(days=5)),
        ("30d", timedelta(days=30)),
        ("500.0d", timedelta(days=500)),
        # Negative values
        ("-50us", timedelta(microseconds=-50)),
        ("-500ms", timedelta(milliseconds=-500)),
        ("-5s", timedelta(seconds=-5)),
        ("-30m", timedelta(minutes=-30)),
        ("-3h", timedelta(hours=-3)),
        ("-1d", timedelta(days=-1)),
        # Compound
        pytest.param(
            "1s 10m 1h", timedelta(seconds=1, minutes=10, hours=1),
            marks=pytest.mark.xfail(reason="Need to improve string parsing")
        ),
        pytest.param(
            "1s10m1h", timedelta(seconds=1, minutes=10, hours=1),
            marks=pytest.mark.xfail(reason="Need to improve string parsing")
        ),
    ]
)
def test_good_parse_timedelta(input: str, expected: timedelta):
    parsed = parse_timedelta(input)
    assert parsed == expected

@pytest.mark.parametrize(
    "input, exception",
    [
        (123, AssertionError),
        (None, AssertionError),
        ('not valid chars', RuntimeError),
        ("0,5s", RuntimeError),
        ("1s with extra chars", RuntimeError)
    ]
)
def test_bad_parse_timedelta(input: str, exception):
    with pytest.raises(exception, match=re.escape(_UNABLE_TO_PARSE_MESSAGE % input)):
        parse_timedelta(input)


@pytest.mark.parametrize(
    "input, expected",
    [
        # Micro seconds
        (timedelta(microseconds=5), "5us"),
        (timedelta(microseconds=500), "500us"),
        # Milliseconds
        (timedelta(milliseconds=50), "50000us"), # NOTE: Timedelta does this mapping under the hood
        # Seconds
        (timedelta(seconds=0.5), "500000us"), # NOTE: Timedelta does this mapping under the hood
        (timedelta(seconds=1), "1s"),
        (timedelta(seconds=5), "5s"),
        (timedelta(seconds=30), "30s"),
        (timedelta(seconds=500), "500s"),
        # Minutes
        (timedelta(minutes=5), "300s"),
        # Hours
        (timedelta(hours=1), "3600s"),
        # Days
        (timedelta(days=1), "1d"),
        (timedelta(days=10), "10d"),
        (timedelta(days=365), "365d"),
        # Compound
        (timedelta(days=3, seconds=30, microseconds=500), "3d 30s 500us")
    ]
)
def test_to_timedelta_str(input: timedelta, expected: str):
    string = to_timedelta_str(input)

    assert string == expected