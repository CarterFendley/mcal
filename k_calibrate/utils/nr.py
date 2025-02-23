from datetime import datetime, timezone


def timestamp_to_datetime(timestamp: float) -> datetime:
    # NOTE: If tz is not provided `fromtimestamp(...)` will convert the UTC epoch timestamp to the current locale
    return datetime.fromtimestamp(timestamp * 0.001, tz=timezone.utc)