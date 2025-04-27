import os
import time
from datetime import timedelta
from typing import Optional

import pandas as pd

from mcal import Sampler
from mcal.utils.time import parse_timedelta


class _DummySampler(Sampler):
    """Dummy sampler used for multipurpose testing"""
    def __init__(
        self,
        delay: Optional[float] = None,
        value: str = 'none',
        id_type: Optional[str] = None,
        id_timeout: str = '1m',
        column_types: Optional[str] = None,
    ):
        self.samples = 0
        self.delay = delay

        if value == 'none':
            self.value = lambda: None
        elif value == 'sample_num':
            self.value = lambda: self.samples
        elif value == 'numbers_repeated':
            # Repeats the number 2 times
            self.value = lambda: self.samples // 2
        else:
            raise NotImplementedError("Return type is not implemented: %s" % self.value)

        if id_type is None:
            self.id = None
        elif id_type == 'sample_num':
            self.id = lambda value: self.samples
        elif id_type == 'odd_even':
            self.id = lambda value: 'even' if value % 2 == 0 else 'odd'
        else:
            raise NotImplementedError("Id type is not implemented: %s" % id_type)

        if column_types is None:
            self.column_types = None
        elif column_types == 'sample_num':
            assert value == 'sample_num', "Column type 'sample_num' should only be used when return values are set to the same type."
            self.column_types = column_types
        else:
            raise NotImplementedError("Column type is not implemented: %s" % column_types)

        # Important that this is on the class
        self.__class__.ID_TIMEOUT = parse_timedelta(id_timeout)

    def sample(self) -> pd.DataFrame:
        if self.delay is not None:
            time.sleep(self.delay)

        value = self.value()
        if self.column_types is None:
            df = pd.DataFrame([{'dummy': value}])
        elif self.column_types == 'sample_num':
            df = pd.DataFrame([{f'{value}': value}])

        if self.id is not None:
            df["id"] = self.id(value)

        self.samples += 1
        return df

class _DummyFileCount(Sampler):
    def __init__(self, directory: str):
        self.directory = directory

    def sample(self) -> pd.DataFrame:
        return pd.DataFrame([{
            'file_count': len(os.listdir(self.directory))
        }])