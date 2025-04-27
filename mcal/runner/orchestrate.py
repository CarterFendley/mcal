import asyncio

import pandas as pd

from mcal.config import MCalConfig
from mcal.events import emit
from mcal.utils.logging import get_logger
from mcal.utils.time import utc_now

from .models import CalibrationRun, RunStats, SamplerData

logger = get_logger(__name__)

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
            sampler._run_sampler() for sampler in samplers.values()
        ]

        watcher_tasks = []
        for task in asyncio.as_completed(tasks):
            sample_data = await task
            name = sample_data.source_name

            if sample_data.raw_data.empty:
                continue

            existing_data = run_data.collected_data[name]
            if existing_data is not None:
                if not existing_data.raw_data.dtypes.equals(sample_data.raw_data.dtypes):
                    logger.warning("Sample from '%s' rejected due to differing schema:\nOLD:\n%s\n\nNEW:\n%s" % (
                        name,
                        existing_data.raw_data.dtypes,
                        sample_data.raw_data.dtypes
                    ))
                    continue

                new_ids, returned_ids = existing_data.append(sample_data)
            else:
                run_data.collected_data[name] = sample_data
                existing_data = sample_data
                new_ids = sample_data.ids["id"]
                returned_ids = pd.Series()

            # Send to subscribed watchers
            timedout = existing_data.preform_timeout()
            watcher_tasks.append(asyncio.create_task(
                _notify_watchers(sample_data, new_ids, returned_ids, timedout)
            ))

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

async def _chain(*args):
    for arg in args:
        await arg

async def _notify_watchers(
    sample_data: SamplerData,
    new_ids: pd.Series,
    returned_ids: pd.Series,
    gone_ids: pd.Series
):
    unordered_tasks = []
    unordered_tasks.append(
        asyncio.create_task(emit(
            (sample_data.source_type, "new-sample"),
            kind=sample_data.source_type,
            records=sample_data.data
        ))
    )

    raw_data = sample_data.raw_data
    updates_issues = []
    first_id_records = (
        raw_data[raw_data['id'].isin(new_ids)]
        .groupby("id")
        .head(1)
    )
    for _, record in first_id_records.iterrows():
        # NOTE: Chain is used b/c the order of id-found / id-updates is strictly defined.
        unordered_tasks.append(asyncio.create_task(_chain(
            emit(
                (sample_data.source_type, "id-found"),
                kind=sample_data.source_type,
                id=record['id'],
                record=record.drop("id")
            ),
            emit(
                (sample_data.source_type, "id-updates"),
                kind=sample_data.source_type,
                id=record['id'],
                records=raw_data[raw_data['id'] == record['id']].drop(columns='id')
            )
        )))

        # Keep track of all updated ids for later
        updates_issues.append(record['id'])

    returned_id_records = (
        raw_data[raw_data['id'].isin(returned_ids)]
        .groupby("id")
        .head(1)
    )
    for _, record in returned_id_records.iterrows():
        # NOTE: Chain is used b/c the order of id-returned / id-updates is strictly defined.
        unordered_tasks.append(asyncio.create_task(_chain(
            emit(
                (sample_data.source_type, "id-returned"),
                kind=sample_data.source_type,
                id=record['id'],
                record=record.drop("id")
            ),
            emit(
                (sample_data.source_type, "id-updates"),
                kind=sample_data.source_type,
                id=record['id'],
                records=raw_data[raw_data['id'] == record['id']].drop(columns='id')
            )
        )))

        updates_issues.append(record['id'])

    # For any record which did not get newly or re-discovered, issue updates for those also
    simple_updates = (
        raw_data[~raw_data['id'].isin(updates_issues)]
    )
    for id, records in simple_updates.groupby('id'):
        # Note no _chain(...) use here
        unordered_tasks.append(asyncio.create_task(
            emit(
                (sample_data.source_type, "id-updates"),
                kind=sample_data.source_type,
                id=id,
                records=records.drop(columns='id')
            )
        ))

    for gone_id in gone_ids.values:
        unordered_tasks.append(asyncio.create_task(
            emit(
                (sample_data.source_type, "id-gone"),
                kind=sample_data.source_type,
                id=gone_id
            )
        ))
    
    await asyncio.gather(*unordered_tasks)