import os
import time
from typing import Optional

import pandas as pd

from mcal.calibrate import Sampler


class _DummySampler(Sampler):
    """Dummy sampler used for multipurpose testing"""
    def __init__(
        self,
        delay: Optional[float] = None,
        value: str = 'none',
        error_at: Optional[int] = None,
    ):
        self.samples = 0
        self.delay = delay

        if value == 'none':
            self.value = lambda: None
        elif value == 'sample_num':
            self.value = lambda: self.samples
        else:
            raise NotImplementedError("Return type is not implemented: %s" % self.value)

    def sample(self) -> pd.DataFrame:
        if self.delay is not None:
            time.sleep(self.delay)

        df = pd.DataFrame([{'dummy': self.value()}])
        self.samples += 1
        return df

class _DummyFileCount(Sampler):
    def __init__(self, directory: str):
        self.directory = directory

    def sample(self) -> pd.DataFrame:
        return pd.DataFrame([{
            'file_count': len(os.listdir(self.directory))
        }])