import time
from typing import Optional

from k_calibrate.calibrate import Sample, Sampler


class _DummySampler(Sampler):
    def __init__(self, delay: Optional[float] = None):
        self.delay = delay

    def sample(self):
        if self.delay is not None:
            time.sleep(self.delay)

        return Sample(data_points={})