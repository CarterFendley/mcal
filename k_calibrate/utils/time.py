import re
from datetime import datetime, timedelta, timezone


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)

# Reference: https://stackoverflow.com/a/4628148/11325551
regex = re.compile(r'((?P<hours>\d+?)hr)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?')
def parse_timedelta(time: str) -> timedelta:
    parts = regex.match(time)
    if not parts:
        raise RuntimeError("Unable to parse '%s' as timedelta" % time)
    parts = parts.groupdict()
    time_params = {}
    for name, param in parts.items():
        if param:
            time_params[name] = int(param)
    return timedelta(**time_params)