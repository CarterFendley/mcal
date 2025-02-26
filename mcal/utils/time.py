import re
from datetime import datetime, timedelta, timezone

from .logging import get_logger

logger = get_logger(__name__)

def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)

# Note:  Original implementation from here: https://stackoverflow.com/a/4628148/11325551
# NOTE: Important that 'ms' is before 'm'
_UNABLE_TO_PARSE_MESSAGE = "Unable to parse '%s' as timedelta: expected string (0.5s, 1s, 2m, 3d)."
regex = re.compile(r'((?P<days>(-)?\d+(\.\d+)?)d)?((?P<hours>(-)?\d+(\.\d+)?)h)?((?P<milliseconds>(-)?\d+(\.\d+)?)ms)?((?P<minutes>(-)?\d+(\.\d+)?)m)?((?P<seconds>(-)?\d+(\.\d+)?)s)?((?P<microseconds>(-)?\d+(\.\d+)?)us)?')
def parse_timedelta(time: str) -> timedelta:
    # TODO:
    # 1. Allow for parts to be separated by whitespace
    # 2. Allow for parts to be in arbitrary order
    assert isinstance(time, str),  _UNABLE_TO_PARSE_MESSAGE % time
    parts = regex.fullmatch(time)
    if not parts:
        raise RuntimeError(_UNABLE_TO_PARSE_MESSAGE % time)
    parts = parts.groupdict()
    time_params = {}

    if all(map(lambda value: value is None,  parts.values())):
        raise RuntimeError(_UNABLE_TO_PARSE_MESSAGE % time)

    for name, param in parts.items():
        if param:
            time_params[name] = float(param)
    return timedelta(**time_params)

def to_timedelta_str(time: timedelta) -> str:
    parts = []
    if time.days != 0:
        parts.append(f'{time.days}d')
    if time.seconds != 0:
        parts.append(f'{time.seconds}s')
    if time.microseconds != 0:
        parts.append(f'{time.microseconds}us')

    if len(parts) == 0:
        return '0s'
    elif len(parts) > 1:
        logger.warning("Timedelta strings with more than one part will currently not be parse-able by `parse_timedelta(...)`")

    return ' '.join(parts)