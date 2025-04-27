from __future__ import annotations

import asyncio
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from importlib.metadata import entry_points
from itertools import compress
from typing import TYPE_CHECKING, Dict, Optional, Tuple, Type, Union

import pandas as pd

from mcal.utils.logging import LogDeduplicate, get_logger
from mcal.utils.pandas import load_dtypes, save_dtypes
from mcal.utils.time import utc_now

if TYPE_CHECKING:
    from mcal.config import SamplerConfig

logger = get_logger(__name__)
dedup = LogDeduplicate()

_LOADED_SAMPLERS: Optional[Dict[str, Sampler]] = None

class Sampler(ABC):
    ID_TIMEOUT: timedelta = timedelta(minutes=30)
    config: SamplerConfig

    def __init__(self):
        pass

    @abstractmethod
    def sample(self) -> Union[pd.Series, pd.DataFrame]:
        pass

    async def _run_sampler(self) -> SamplerData:
        """
        Small wrapper for sampler execution to:
        1. Make synchronous sampler async.
        2. Do post processing on the sampler output
            -> Add timestamp if not supplied
            -> Create `SamplerData` object from DataFrame / Series
    
        Returns:
            SamplerData: The sampler data returned by the sampler
        """
        loop = asyncio.get_running_loop()

        # NOTE: This is to prevent this from being a blocking call, allowing other async tasks to make progress
        # Reference: https://stackoverflow.com/a/43263397/11325551
        sample_time = utc_now()
        sample = await loop.run_in_executor(None, self.sample)

        assert isinstance(sample, (pd.Series, pd.DataFrame)), "Sampler '%s' returned value which is not an instance of 'Sample': %s" % (self.__class__.__name__, sample)

        if isinstance(sample, pd.Series):
            sample = sample.to_frame().T

        if 'timestamp' not in sample.columns:
            sample['timestamp'] = sample_time
        else:
            assert pd.api.types.is_datetime64_any_dtype(sample['timestamp']), f"Sampler '{self.__class__.__name__}' returned 'timestamp' which is not an instance of datetime"

        return SamplerData.from_dataframe(
            source_name=self.config.get_name(),
            df=sample,
            source_type=type(self)
        )

@dataclass
class SamplerData:
    raw_data: pd.DataFrame
    ids: pd.DataFrame
    source_name: str
    source_type: Optional[Type[Sampler]]

    @classmethod
    def from_dataframe(
        cls,
        source_name: str,
        df: pd.DataFrame,
        source_type: Optional[Type[Sampler]] = None
    ) -> SamplerData:
        if "id" not in df.columns:
            dedup(logger.warning, "Source '%s' supplied DataFrame without 'id', setting id column to source name." % source_name)
            df["id"] = source_name

        # Create ids df by grabbing latest timestamp from each
        ids = df[["id", "timestamp"]]
        ids = ids.groupby(["id"]).tail(1).rename(columns={'timestamp': 'last_seen'})
        ids["present"] = True # TODO: Make this a computation?

        data = cls(
            raw_data=df,
            ids=ids,
            source_name=source_name,
            source_type=source_type,
        )

        return data

    @property
    def data(self) -> pd.DataFrame:
        # TODO: This is probably inefficient for consecutive calls without mutation to `raw_data`.
        return self.raw_data.drop(columns='id')

    def append(self, other: SamplerData) -> Tuple[pd.Series, pd.Series]:
        """
        Append other `SamplerData` to this one, returning a list of new ids found in the other data.

        Args:
            other (SamplerData): The other sampler data to append to this one.

        Returns:
            Set[str]: A set of ids which were introduced by `other.
        """
        assert len(other.ids[other.ids["present"] == False]) == 0, "Unexpected usage of append, `other` object should always be from most recent sample"

        # Note that we are only selecting the '"id"' column from the ids dataframe for each of these
        ids_returned = self.ids[self.ids["present"] == False]
        ids_returned = ids_returned[ids_returned["id"].isin(other.ids["id"])]["id"]
        ids_new = other.ids[~other.ids["id"].isin(self.ids["id"])]["id"]

        self.ids = pd.concat(
            [
                # NOTE: Order is important here since we are only keeping head(1)
                other.ids,
                self.ids
            ],
            ignore_index=True, # Don't 100% understand this param
        )
        self.ids = self.ids.groupby("id").head(1) # Keep one record per id, preferring the ones from `other` which should be the newer dataframe.

        self.raw_data = pd.concat(
            [
                self.raw_data,
                other.raw_data
            ],
            ignore_index=True, # Don't 100% understand this param
        )

        return ids_new, ids_returned

    def preform_timeout(self) -> pd.Series:
        assert self.source_type is not None, "Can not read ID_TIMEOUT since source type is None"

        self.ids["age"] = utc_now() - self.ids['last_seen']
        self.ids["present_update"] = self.ids["age"] <= self.source_type.ID_TIMEOUT

        logger.debug("IDs ages:\n%s" % self.ids)

        timedout = self.ids[self.ids["present"] != self.ids["present_update"]]
        assert len(timedout[timedout["present_update"] == True]) == 0, "Internal error, `preform_timeout` would have caused present to go from False to True."

        # Clean up intermediate columns
        self.ids.drop(columns=["age", "present"], inplace=True)
        self.ids.rename(columns={"present_update": "present"}, inplace=True)

        return timedout["id"]

    def write(self, folder_path: str, file_type: str = "csv"):
        if file_type == 'csv':
            path = os.path.join(folder_path, self.source_name + ".csv")
            dtypes_path = dtypes_path = os.path.join(folder_path, self.source_name + '_dtypes.json')
            self.raw_data.to_csv(path)
            save_dtypes(dtypes_path, self.raw_data)
        else:
            raise NotImplementedError("SampleData saving not implemented for file type: '%s'" % file_type)

    @classmethod
    def load(
        cls,
        file_path: str,
    ) -> SamplerData:
        name, ext = os.path.splitext(file_path)
        folder, name = name.rsplit(os.sep, 1)

        if ext == '.csv':
            dtypes_path = os.path.join(folder, name + "_dtypes.json")
            if not os.path.isfile(dtypes_path):
                msg = "File at '%s' should be accompanied by dtypes file at path '%s' but none found" % (file_path, dtypes_path)
                logger.error(msg)
                raise RuntimeError(msg)

            dtypes_dict, parse_dates = load_dtypes(dtypes_path)
            df = pd.read_csv(
                file_path,
                dtype=dtypes_dict,
                parse_dates=parse_dates,
                index_col=0 # Avoids 'Unnamed: 0' from showing up
            )
            return cls.from_dataframe(
                source_name=name,
                df=df
            )
        else:
            raise NotImplementedError("SamplerData loading not implemented for file type: '%s'" % ext)


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
    global _LOADED_SAMPLERS
    if _LOADED_SAMPLERS is None or reload:
        _load_samplers()

    return name in _LOADED_SAMPLERS

def get_sampler(name: str, reload: bool = False) -> Optional[Type[Sampler]]:
    global _LOADED_SAMPLERS
    if _LOADED_SAMPLERS is None or reload:
        _load_samplers()

    return _LOADED_SAMPLERS.get(name)