from abc import ABC

import pandas as pd


class Watcher(ABC):
    # TODO: Assure single threaded for ease
    def after_sample(self, name: str, sample: pd.DataFrame):
        """Run after sample is returned, before added to run data"""
        pass

class _DummyWatcher(Watcher):
    def __init__(self):
        self.samples = 0
    # Made to be used _DummySampler
    def after_sample(self, name: str, sample: pd.DataFrame):
        if name == '_DummySampler':
            assert sample.shape == (1, 2)
            sample_num = sample['dummy'].iloc[0]
            assert sample_num == self.samples

            print("Watcher found sample number:", sample_num)

            self.samples += 1
        else: 
            print("Found unexpected sampler: %s" % name)