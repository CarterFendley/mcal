import asyncio
from typing import Tuple

import pandas as pd

from mcal.calibrate import Sampler
from mcal.config import MCalConfig
from mcal.utils.logging import get_logger
from mcal.utils.time import utc_now

from .models import CalibrationRun, RunStats

logger = get_logger(__name__)


async def _run_sampler(
    name: str,
    sampler: Sampler
) -> Tuple[str, pd.DataFrame]:
    # Small async wrapper for sampler execution
    loop = asyncio.get_running_loop()

    sample_time = utc_now()
    # NOTE: This is to prevent this from being a blocking call, allowing other async tasks to make progress
    # Reference: https://stackoverflow.com/a/43263397/11325551
    sample = await loop.run_in_executor(None, sampler.sample)

    assert isinstance(sample, (pd.Series, pd.DataFrame)), "Sampler '%s' returned value which is not an instance of 'Sample': %s" % (sampler.__class__.__name__, sample)

    if isinstance(sample, pd.Series):
        sample = sample.to_frame().T

    if 'timestamp' not in sample.columns:
        sample['timestamp'] = sample_time
    else:
        assert pd.api.types.is_datetime64_any_dtype(sample['timestamp']), f"Sampler '{name}' returned 'timestamp' which is not an instance of datetime"

    return name, sample

async def run(
    config: MCalConfig,
) -> CalibrationRun:
    schedule, samplers, watchers, actions, stop_criteria = config.create()

    # Create run data object and pre-allocate space in the data dict
    run_data = CalibrationRun(
        start_time=utc_now(),
        config=config
    )
    for name in samplers.keys():
        run_data.collected_data[name] = None

    stats = RunStats()
    logger.info("Starting run loop...")
    if stop_criteria is None:
        logger.warning("No stop criteria has been provided, loop will iterate infinitely...")
    while stop_criteria is None or not stop_criteria(stats):
        # NOTE: Given the structure of schedules, the fact that we don't pass any "start_time" it is useful to call sleep at the start of the loop so it may capture that or similar concepts without any parameter passing here.
        # NOTE: Schedulers are currently using thread.sleep not asyncio.sleep because this is the outer most async loop and there is nothing else important to make progress.
        schedule.sleep()
        logger.debug("Iteration %s", stats.iterations + 1)

        tasks = [
            _run_sampler(name, sampler) for name, sampler in samplers.items()
        ]
        watcher_loop = asyncio.get_running_loop()
        watcher_tasks = []
        for task in asyncio.as_completed(tasks):
            name, sample = await task

            existing_df = run_data.collected_data[name]
            if run_data.collected_data[name] is not None:
                assert existing_df.dtypes.equals(sample.dtypes), "Sampler returned different datatypes on different executions"
            else:
                existing_df = pd.DataFrame()

            # Send to watchers
            for watcher in watchers:
                watcher_task = watcher_loop.run_in_executor(
                    None,
                    watcher.after_sample,
                    name,
                    sample
                )
                watcher_tasks.append(watcher_task)

            if not sample.empty:
                # Don't add empty data frames for a couple of reasons
                # 1. Useless call
                # 2. Will mess up the above check asserting dtypes are the same if a sampler does not have data for one iteration
                #   -> Don't want to require sampler writers to always have the right schema
                run_data.collected_data[name] = pd.concat(
                    [
                        existing_df,
                        sample,
                    ],
                    ignore_index=True, # Don't 100% understand this param
                )

        # Run all action's after_inter method
        loop = asyncio.get_running_loop()
        action_tasks = []
        for action in actions:
            task = loop.run_in_executor(None, action.after_iter, stats)
            if action.AWAIT_AFTER_ITER:
                action_tasks.append(task)

        # Wait for actions to complete
        await asyncio.gather(*action_tasks)
        # Wait for watchers to complete
        await asyncio.gather(*watcher_tasks)


        stats.iterations += 1
        stats.time_elapsed = utc_now() - run_data.start_time

        # TODO: Store checkpointed data

    logger.info("Run ended successfully:\n%s" % stats.get_str())

    return run_data