from __future__ import annotations

import os
import time
from abc import ABC
from typing import TYPE_CHECKING, Callable, Type

if TYPE_CHECKING:
    # Run stats uses the 'mcal.config' module which also uses this class causing a circular import
    from mcal.runner.models import RunStats

class Action(ABC):
    AWAIT_AFTER_ITER = True

    def after_iter(self, stats: RunStats):
        pass

    # TODO: Move the after_iter here

def action(func: Callable) -> Type[Action]:
    class ActionGenerator(Action):
        def run(stats: RunStats):
            func(stats)

    return ActionGenerator

class _DummyFileCreate(Action):
    def __init__(self, directory: str, prefix: str = ''):
        self.directory = directory
        self.prefix = prefix

    def after_iter(self, stats: RunStats):
        file_path = os.path.join(
            self.directory,
            f'{self.prefix}{stats.iterations}.txt')
        with open(file_path, 'w') as f:
            pass

class _DummySleepAction(Action):
    def __init__(self, delay: float):
        self.delay = delay

    def after_iter(self, stats: RunStats):
        time.sleep(self.delay)

class _DummyNoAwait(_DummySleepAction):
    AWAIT_AFTER_ITER = False