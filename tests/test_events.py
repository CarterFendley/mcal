import asyncio
import time

import pandas as pd
import pytest

from mcal.events import clear_subscriptions, emit, on_event


def test_simple_event():
    clear_subscriptions()

    received = None

    @on_event('simple-event')
    def simple_event_listener(row: pd.Series):
        nonlocal received

        received = row

    task = emit('simple-event', 1)
    asyncio.get_event_loop().run_until_complete(
        task
    )

    assert received == 1

@pytest.mark.parametrize(
    "sleep_time",
    (
        0.2,
        0.3,
        pytest.param(1, marks=pytest.mark.slow),
        pytest.param(2, marks=pytest.mark.slow),
        pytest.param(3, marks=pytest.mark.slow)
    )
)
def test_async_listener(sleep_time: float):
    clear_subscriptions()

    count = 0
    concurrent_observed = False

    @on_event('simple-event')
    async def listener(id: int):
        nonlocal count
        nonlocal concurrent_observed
        count += 1

        # Divide sleep into five intervals and check each time
        for _ in range(5):
            if count != 1: # Good!
                concurrent_observed = True
            await asyncio.sleep(sleep_time/5)

        count -= 1


    tasks = (
        emit('simple-event', 0),
        emit('simple-event', 1)
    )
    asyncio.get_event_loop().run_until_complete(
        asyncio.gather(*tasks)
    )

    assert concurrent_observed, "No current executions observed of async listener"

@pytest.mark.parametrize(
    "sleep_time",
    (
        0.2,
        0.3,
        pytest.param(1, marks=pytest.mark.slow),
        pytest.param(2, marks=pytest.mark.slow),
        pytest.param(3, marks=pytest.mark.slow)
    )
)
def test_sync_no_reentrant(sleep_time: float):
    clear_subscriptions()

    count = 0

    @on_event('simple-event')
    def listener():
        nonlocal count
        count += 1

        # Devide sleep into five intervals and check each time
        for _ in range(5):
            time.sleep(sleep_time/5)
            assert count == 1, "Multiple concurrent invocations of synchronous loop"

        count -= 1

    tasks = (
        emit('simple-event'),
        emit('simple-event')
    )
    asyncio.get_event_loop().run_until_complete(
        asyncio.gather(*tasks)
    )

@pytest.mark.xfail
@pytest.mark.parametrize(
    "sleep_time",
    (
        0.2,
        0.3,
        pytest.param(1, marks=pytest.mark.slow),
        pytest.param(2, marks=pytest.mark.slow),
        pytest.param(3, marks=pytest.mark.slow)
    )
)
def test_sync_no_reentrant_multi_event(sleep_time: float):
    clear_subscriptions()

    count = 0

    @on_event('simple-event')
    @on_event('another-event')
    def listener():
        nonlocal count
        count += 1

        # Devide sleep into five intervals and check each time
        for _ in range(5):
            time.sleep(sleep_time/5)
            assert count == 1, "Multiple concurrent invocations of synchronous loop"

        count -= 1

    tasks = (
        emit('simple-event'),
        emit('another-event')
    )
    asyncio.get_event_loop().run_until_complete(
        asyncio.gather(*tasks)
    )

