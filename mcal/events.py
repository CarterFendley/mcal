from __future__ import annotations

import asyncio
import functools
import inspect
from typing import Callable, Dict, Hashable, List

from mcal.utils.logging import get_logger

ASYNC_EVENT_LISTENERS: Dict[Hashable, List[Callable]] = {}
SYNC_EVENT_LISTENERS: Dict[Hashable, List[SyncListenerFeeder]] = {}

logger = get_logger(__name__)

def clear_subscriptions():
    global ASYNC_EVENT_LISTENERS
    global SYNC_EVENT_LISTENERS

    ASYNC_EVENT_LISTENERS = {}
    SYNC_EVENT_LISTENERS = {}

class SyncListenerFeeder:
    """Designed invoke synchronous without them needing to be reentrant"""

    def __init__(self, func: Callable):
        self.func = func

        self.lock = asyncio.Lock()

    async def __call__(self, *args, **kwargs):
        async with self.lock:
            func = functools.partial(self.func, *args, **kwargs)
            await asyncio.get_running_loop().run_in_executor(
                None,
                func
            )


# TODO: Maybe preform upfront detection of signature and match to a protocol
def on_event(event: Hashable) -> Callable:
    def _on_event(func: Callable) -> Callable:
        if inspect.iscoroutinefunction(func):
            if event not in ASYNC_EVENT_LISTENERS:
                ASYNC_EVENT_LISTENERS[event] = []
            ASYNC_EVENT_LISTENERS[event].append(
                func
            )
        else:
            if event not in SYNC_EVENT_LISTENERS:
                SYNC_EVENT_LISTENERS[event] = []
            SYNC_EVENT_LISTENERS[event].append(
                SyncListenerFeeder(func)
            )

        return func

    return _on_event

async def emit(event: Hashable, *args, **kwargs):
    tasks = []
    for listener in SYNC_EVENT_LISTENERS.get(event, ()):
        tasks.append(listener(*args, **kwargs))
    for listener in ASYNC_EVENT_LISTENERS.get(event, ()):
        tasks.append(listener(*args, **kwargs))

    try:
        await asyncio.gather(*tasks)
    except Exception as err:
        msg = (
            "Failed to invoke all listeners!"
            f"\n\t- Event: {event}"
            f"\n\t- Arguments: {args}"
            f"\n\t- Kwargs: {kwargs}"
        )
        logger.error(msg)
        raise err