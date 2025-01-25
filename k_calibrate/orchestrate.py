import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import pandas as pd

from k_calibrate.calibrate import Sample, Sampler
from k_calibrate.config import KCConfig, load_config_file
from k_calibrate.utils.logging import get_logger
from k_calibrate.utils.pandas import load_dtypes, save_dtypes
from k_calibrate.utils.time import utc_now

# NOTE: I think it is important that %Z is included to assure UTC
DATE_FORMAT = "%Y-%m-%d_%H:%M:%S_%Z"

logger = get_logger(__name__)

# TODO: Unify with / include in CalibrationRun
@dataclass
class RunStats:
    time_elapsed: timedelta = timedelta(seconds=0)
    iterations: int = 0

    def get_str(self) -> str:
        return "\t" + "\n\t".join((
            f"Iterations: {self.iterations}",
            f"Time elapsed: {self.time_elapsed}",
        ))

@dataclass
class CalibrationRun:
    start_time: datetime
    config: KCConfig
    collected_data: Dict[str, pd.DataFrame] = field(default_factory=lambda: {})

    def gen_name(self) -> str:
        return self.start_time.strftime(DATE_FORMAT)

    def write_run(
        self,
        save_directory: Optional[str] = None,
        name: Optional[str] = None,
        data_type: str = 'csv'
    ) -> str:
        if save_directory is None:
            save_directory = 'kc_run_data'
        if name is None:
            name = self.gen_name()

        folder_path = os.path.join(save_directory, name)
        if os.path.exists(folder_path):
            # TODO: Remove this, really bad to error if run has data
            raise RuntimeError("Write path already exists: %s", folder_path)

        os.makedirs(folder_path)
        logger.info("Writing sample run to directory: %s" % folder_path)

        config_path = os.path.join(folder_path, "config.yml")
        self.config.save(config_path)

        for sample_name, sample in self.collected_data.items():
            if data_type == 'csv':
                path = os.path.join(folder_path, sample_name + ".csv")
                dtypes_path = os.path.join(folder_path, sample_name + '_dtypes.json')
                sample.to_csv(path, header=True)
                save_dtypes(dtypes_path, sample)
            else:
                raise NotImplementedError("Run saving not implemented for type: %s" % data_type)

        return folder_path

def load_run(path: str) -> CalibrationRun:
    try:
        folder_name = os.path.basename(path)
        start_time = datetime.strptime(folder_name, DATE_FORMAT)
    except ValueError:
        start_time = None

    config = None
    collected_data = {}
    for file in os.listdir(path):
        file_path = os.path.join(path, file)
        if file == "config.yml":
            # NOTE: Config file should be fully rendered when saved
            config = load_config_file(file_path, {})
            continue

        name, ext = os.path.splitext(file)

        if ext == ".json":
            # Used for saving CSV dtypes so just skipping here
            continue
        if ext == ".csv":
            dtypes_path = os.path.join(path, name + "_dtypes.json")
            if not os.path.isfile(dtypes_path):
                logger.error("Found csv file '%s' but no accompanying dtypes file at path: %s" % (file, dtypes_path))
                raise RuntimeError("Found CSV file but no dtypes file, is your data corrupted.")
            dtypes_dict, parse_dates = load_dtypes(dtypes_path)
            collected_data[name] = pd.read_csv(
                file_path,
                dtype=dtypes_dict,
                parse_dates=parse_dates
            )
        else:
            raise NotImplementedError("Found unexpected type in save folder: %s" % ext)

    if config is None:
        # TODO: Definitely can optimize this if data load times get larger
        raise RuntimeError("Unable to find 'config.yml' file in directory: %s" % path)
    if len(collected_data) == 0:
        logger.warning("Not sample data was found in directory, returning a sample run with empty data: %s" % path)

    return CalibrationRun(
        start_time=start_time,
        config=config,
        collected_data=collected_data
    )

async def _run_sampler(name: str, sampler: Sampler) -> Tuple[str, Sample]:
    # Small async wrapper for sampler execution
    loop = asyncio.get_running_loop()

    sample_time = utc_now()
    # NOTE: This is to prevent this from being a blocking call, allowing other async tasks to make progress
    # Reference: https://stackoverflow.com/a/43263397/11325551
    sample = await loop.run_in_executor(None, sampler.sample)

    assert isinstance(sample, Sample), "Sampler '%s' returned value which is not an instance of 'Sample': %s" % (sampler.__class__.__name__, sample)

    if sample.timestamp is None:
        sample.timestamp = sample_time

    return name, sample

async def run(
    config: KCConfig,
) -> CalibrationRun:
    schedule, samplers, actions, stop_criteria = config.create()

    # Create run data object and allocate dataframes
    run_data = CalibrationRun(
        start_time=utc_now(),
        config=config
    )
    for name in samplers.keys():
        df = pd.DataFrame()
        df.index.name = 'iteration'
        run_data.collected_data[name] = df

    stats = RunStats()
    while not stop_criteria(stats):
        # NOTE: Given the structure of schedules, the fact that we don't pass any "start_time" it is useful to call sleep at the start of the loop so it may capture that or similar concepts without any parameter passing here.
        # NOTE: Schedulers are currently using thread.sleep not asyncio.sleep because this is the outer most async loop and there is nothing else important to make progress.
        schedule.sleep()
        logger.info("Iteration %s", stats.iterations + 1)

        tasks = [
            _run_sampler(name, sampler) for name, sampler in samplers.items()
        ]
        for task in asyncio.as_completed(tasks):
            name, sample = await task

            # Store as new row
            run_data.collected_data[name] = pd.concat(
                [
                    run_data.collected_data[name],
                    pd.DataFrame(sample.as_pandas_row()),
                ],
                ignore_index=True, # Don't 100% understand this param
            )

        # Run all actions
        loop = asyncio.get_running_loop()
        tasks = [
            loop.run_in_executor(None, action, stats) for action in actions
        ]
        # Wait for actions to complete
        await asyncio.gather(*tasks)


        stats.iterations += 1
        stats.time_elapsed = utc_now() - run_data.start_time

        # TODO: Store checkpointed data

    logger.info("Run ended successfully:\n%s" % stats.get_str())

    return run_data