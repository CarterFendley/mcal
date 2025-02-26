from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from importlib.metadata import entry_points
from itertools import compress
from math import ceil
from typing import Any, Dict, List, Optional, Type, Union

import pandas as pd
from timedelta import Timedelta

from mcal.utils.logging import get_logger
from mcal.utils.time import parse_timedelta, utc_now

logger = get_logger(__name__)

DETAILED_FORMAT = '%m/%d/%y %H:%M:%S.%f'

class Sampler(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def sample(self) -> Union[pd.Series, pd.DataFrame]:
        pass

_LOADED_SAMPLERS: Optional[Dict[str, Sampler]] = None

def _load_samplers() -> Dict[str, Sampler]:
    samplers = {}
    eps = entry_points(group='mcal.samplers')
    for ep in eps:
        try:
            entry_point_data = ep.load()
        except IndexError:
            logger.warning(f"Failed to load entrypoint: {ep}")
            continue

        # Preform assertions
        if not isinstance(entry_point_data, list):
            logger.warning(f"Entrypoint did not contain list: {ep}")
            continue

        not_samplers = map(lambda v: not issubclass(v, Sampler), entry_point_data)
        not_samplers = tuple(compress(entry_point_data, not_samplers))
        if len(not_samplers) != 0:
            logger.warning(f"Found non-sampler types in entrypoint list: {not_samplers}")
            continue

        for sampler in entry_point_data:
            name = sampler.__name__
            if name in samplers:
                logger.warning(f"Found duplicate name '{name}'. Overriding previous sampler with current version.")
            samplers[name] = sampler

    global _LOADED_SAMPLERS
    _LOADED_SAMPLERS = samplers

    return samplers

def is_sampler(name: str, reload: bool = False) -> bool:
    if _LOADED_SAMPLERS is None or reload:
        _load_samplers()

    return name in _LOADED_SAMPLERS

def get_sampler(name: str, reload: bool = False) -> Optional[Type[Sampler]]:
    if _LOADED_SAMPLERS is None or reload:
        _load_samplers()

    return _LOADED_SAMPLERS.get(name)

class Schedule(ABC):
    @classmethod
    @abstractmethod
    def from_config(
        cls,
        *args,
        **kwargs
    ) -> Schedule:
        # TODO: Why is this not being caught?
        pass

    @abstractmethod
    def sleep(loop_start: datetime):
        pass

class IntervalSchedule(Schedule):
    @classmethod
    def from_config(cls, interval: str) -> IntervalSchedule:
        return cls(interval=parse_timedelta(interval))

    def __init__(self, interval: timedelta):
        self.interval = interval

        self._last_time: datetime = None

        if self.interval.total_seconds() < 0:
            logger.error("Specified interval is negative.")
            raise NotImplementedError("Schedule not implemented for negative intervals")

    def sleep(self):
        # If this is the first loop, return immediately
        # TODO: This assumes that sleep() is called at the start of the loop, although this may be good for IntervalSchedule and even ReferencesIntervalSchedule, it is a tad confusing to see.
        if self._last_time is not None:
            sleep_time = self.interval - (
                utc_now() - self._last_time
            )

            if sleep_time.total_seconds() <= 0:
                logger.warning("Calculated sleep time is not positive, this may indicate the sleep calculation loop is running too slow, returning immediately: %s seconds" % sleep_time.total_seconds())
            else:
                time.sleep(sleep_time.total_seconds())

        self._last_time = utc_now()

class ReferencedIntervalSchedule(Schedule):
    @classmethod
    def from_config(cls):
        raise NotImplementedError("Not yet implemented")

    def __init__(
        self,
        interval: timedelta,
        reference_time: datetime,
        disable_checks: Optional[bool] = False
    ):
        self.interval = Timedelta(interval)
        self.disable_checks = disable_checks
        self.set_reference_clock(reference_time)

        if not disable_checks:
            if self.interval.total_seconds() < 0:
                logger.error("Specified interval is negative.")
                raise NotImplementedError("Schedule not implemented for negative intervals")

        self._last_target: Optional[datetime] = None

    def set_reference_clock(self, reference_time: datetime):
        if not self.disable_checks:
            if reference_time.tzinfo != timezone.utc:
                # TODO: Do some conversions
                logger.error("Reference time must be in UTC time zone, instead received time zone: %s" % reference_time.tzinfo)
                raise NotImplementedError("Reference time must be in UTC.")

            # Quick sanity check for reference clock
            now = utc_now()
            current_delta = Timedelta(now - reference_time)
            if current_delta.total_seconds() < 0:
                logger.error("Reference timestamp is in the future, this violates the assumptions made by this class")
                raise NotImplementedError("Reference time is in future.")
            if current_delta.total_seconds() > (1*3600):
                # NOTE: This is set pretty low (1 hour) to attempt to detect time zone mismatches
                # TODO: Maybe change this to some % of the interval?
                logger.warning("Reference timestamp is greater than one hour old.")

        self.reference_time = reference_time
        # TODO: Figure out how to handle _last_target here, just reset? 

    def sleep(self):
        # Find next interval to target
        now = utc_now()
        now_reference_diff = now - self.reference_time # NOTE: Assertion that this will be positive happens when reference clock is set
        current_target = (
            self.reference_time
            + self.interval * (ceil(now_reference_diff / self.interval))
        )

        # Check to see if any intervals were missed
        if not self.disable_checks and self._last_target is not None:
            next_last_diff = current_target - self._last_target
            intervals_elapsed = ceil(next_last_diff / self.interval)

            if intervals_elapsed > 1:
                missed_targets = map(
                    lambda int_n: (int_n * self.interval) + self._last_target,
                    range(1, intervals_elapsed)
                    # Note that it is not `intervals_elapsed+1` (don't want the last interval as that will be the current target) 
                )
                missed_targets = map(lambda t: t.strftime(DETAILED_FORMAT), missed_targets)
                logger.warning("Missed %s targets, this probably indicates your loop is not running fast enough for the associated interval, the following timestamps will have no executions:\n%s" % (intervals_elapsed-1, "\n".join(missed_targets)))

        # Store for next loop
        self._last_target = current_target

        # Note: The below is re-calculating "now" to attempt to get most accurate sleep time
        time_to_target = current_target - utc_now()
        if time_to_target.total_seconds() <= 0:
            # Not an optional check for my own sanity
            logger.warning("Calculated sleep time is not positive, this may indicate the sleep calculation loop is running too slow, returning immediately: %s seconds" % time_to_target.total_seconds())
            return

        logger.debug("Sleeping for %s seconds to meet target: %s" % (time_to_target.total_seconds(), current_target))
        time.sleep(time_to_target.total_seconds())

SCHEDULES = [
    IntervalSchedule,
    ReferencedIntervalSchedule
]
SCHEDULES = {s.__name__:s for s in SCHEDULES}

def get_schedule(name: str) -> Optional[Type[Schedule]]:
    return SCHEDULES.get(name)

def is_schedule(name: str) -> bool:
    return get_schedule(name) != None

# def run()