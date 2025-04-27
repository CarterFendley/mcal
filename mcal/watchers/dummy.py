import time
from typing import Type

import pandas as pd

from mcal import Sampler
from mcal.samplers.dummy import _DummySampler
from mcal.utils.logging import get_logger
from mcal.watchers import Watcher

logger = get_logger(__name__)

class _DummyWatcher(Watcher):
    # Made to be used _DummySampler
    def __init__(self, delays: dict = None):
        self.subscribe(_DummySampler)
        self.samples = 0

        if delays is None:
            self.delays = {}
        else:
            self.delays = delays

    def new_sample(self, kind: Type[Sampler], records: pd.DataFrame):
        delay = self.delays.get('new-sample')
        if delay is not None:
            time.sleep(delay)

        if kind == _DummySampler:
            assert records.shape == (1, 2)
            sample_num = records['dummy'].iloc[0]
            print('-------')
            print(f"new sample: {sample_num}")

            self.samples += 1
        else:
            raise NotImplementedError("Found unexpected sampler: %s" % kind)

    def id_found(self, kind: Type[Sampler], id: str, record: pd.Series):
        delay = self.delays.get('id-found')
        if delay is not None:
            time.sleep(delay)

        if kind == _DummySampler:
            assert record.shape == (2,)
            print(f"id found: {id}")
        else:
            raise NotImplementedError("Found unexpected sampler: %s", kind)

    def id_returned(self, kind: Type[Sampler], id: str, record: pd.Series):
        delay = self.delays.get('id-returned')
        if delay is not None:
            print("Sleeping")
            time.sleep(delay)

        if kind == _DummySampler:
            print(f"id returned: {id}")
        else:
            raise NotImplementedError("Found unexpected sampler: %s", kind)

    def id_updates(self, kind: Type[Sampler], id: str, records: pd.DataFrame):
        delay = self.delays.get('id-updates')
        if delay is not None:
            time.sleep(delay)

        if kind == _DummySampler:
            print(f"id updated: {id}")
        else:
            raise NotImplementedError("Found unexpected sampler: %s", kind)

    def id_gone(self, kind: Type[Sampler], id: str):
        delay = self.delays.get('id-gone')
        if delay is not None:
            time.sleep(delay)

        if kind == _DummySampler:
            print(f"id gone: {id}")
        else:
            raise NotImplementedError("Found unexpected sampler: %s", kind)