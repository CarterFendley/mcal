import os
import time
from typing import Optional

import pandas as pd

from k_calibrate.calibrate import Sampler


class _DummySampler(Sampler):
    def __init__(self, delay: Optional[float] = None):
        self.delay = delay

    def sample(self) -> pd.DataFrame:
        if self.delay is not None:
            time.sleep(self.delay)

        return pd.DataFrame([{'dummy': None}])

class _DummyFileCount(Sampler):
    def __init__(self, directory: str):
        self.directory = directory

    def sample(self) -> pd.DataFrame:
        return pd.DataFrame([{
            'file_count': len(os.listdir(self.directory))
        }])