from abc import ABC
from typing import Callable, Optional, Type

import pandas as pd

from mcal import Sampler
from mcal.events import on_event

EVENTS = (
    "new-sample",
    "id-found",
    "id-updates",
    "id-gone",
    "id-returned"
)

class Watcher(ABC):
    def subscribe(self, kind: Type[Sampler], method: Callable = None):
        # TODO: Don't overload 'event' here
        if method is not None:
            event = method.__name__
            event = event.replace("_", "-")

            assert event in EVENTS, "Unknown event '%s' please check the method passed to subscribe(...)" % event

            events = {
                event: method
            }
        else:
            # TODO: Check if these methods are implemented for efficiency
            events = {
                "new-sample": self.new_sample,
                "id-found": self.id_found,
                "id-returned": self.id_returned,
                "id-updates": self.id_updates,
                "id-gone": self.id_gone,
            }

        """
        This structure is used instead the `on_event` decorator, because at decoration time (definition time), the functions backing methods do not have instances of the classes (and getting them is hard). Here we can use the `on_event` function and provide a method reference through `self` of this function which will automatically pass the correct instance to the method's `self` parameter.
        """
        for event, method in events.items():
            on_event((kind, event))(method)

    def all_data(self, id: Optional[str] = None) -> pd.DataFrame:
        """
        A helper method to get all historical data, optionally filtered to a specified ID.

        Args:
            id (Optional[str], optional): An option ID to apply as a filter. Defaults to None.

        Returns:
            pd.DataFrame: All historical data for this sampler.
        """
        # TODO: Implement
        raise NotImplementedError("Not implemented")

    def new_sample(self, kind: Type[Sampler], records: pd.DataFrame):
        """
        Called after new samples are collected.

        **NOTE:** This will be called with bulk data from the sampler, if you want to react to data on the ID level use one of the following:
        - `id_found(...)`
        - `id_updates(...)`
        - `id_gone(...)`
        - `id_returned(...)`

        Args:
            kind (Type[Sampler]): Which kind of sampler this set of records came from.
            records (pd.DataFrame): The records from a single sample operation.
        """
        pass

    def id_found(self, kind: Type[Sampler], id: str, record: pd.Series):
        pass

    def id_updates(self, kind: Type[Sampler], id: str, records: pd.DataFrame):
        pass

    def id_gone(self, kind: Type[Sampler], id: str):
        pass

    def id_returned(self, kind: Type[Sampler], id: str, record: pd.Series):
        pass