from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

from k_calibrate.calibrate import Sample
from k_calibrate.config import KCConfig
from k_calibrate.saves import SampleRun
from k_calibrate.utils.logging import get_logger
from k_calibrate.utils.time import utc_now

logger = get_logger(__name__)

# TODO: Unify / move this and k_calibrate.saves.SampleRun
@dataclass
class RunStats:
    time_elapsed: timedelta = timedelta(seconds=0)
    iterations: int = 0

    def get_str(self) -> str:
        return "\t" + "\n\t".join((
            f"Iterations: {self.iterations}",
            f"Time elapsed: {self.time_elapsed}",
        ))

# TODO:
#   1. This should return RunData!
#   2. It should not write the data, that should happen in the CLI
def run(
    config: KCConfig,
    name: Optional[str] = None,
    save_directory: Optional[str] = None
):
    schedule, samplers, stop_criteria = config.create()

    # Go ahead and allocate run data
    run_data = SampleRun(
        start_time=utc_now(),
        config=config
    )
    for sampler_name in samplers.keys():
        df = pd.DataFrame()
        df.index.name = 'iteration'
        run_data.sample_data[sampler_name] = df

    # TODO:
    # 1. Multiple samplers in different threads / processes
    # 2. Passive samplers without schedule
    stats = RunStats()
    while not stop_criteria(stats):
        schedule.sleep()
        logger.info("Iteration: %s", stats.iterations + 1)
        for sampler_name, sampler in samplers.items():
            sample_time = utc_now()
            sample = sampler.sample()

            assert isinstance(sample, Sample), "Sampler '%s' returned value which is not an instance of 'Sample': %s" % (sampler.__class__.__name__, sample)

            if sample.timestamp is None:
                sample.timestamp = sample_time

            # Store new row
            run_data.sample_data[sampler_name] = pd.concat(
                [
                    run_data.sample_data[sampler_name],
                    pd.DataFrame(sample.as_pandas_row()),
                ],
                ignore_index=True # Not 100% on this
            )

        stats.iterations += 1
        stats.time_elapsed = utc_now() - run_data.start_time

    logger.info("Run ended successfully:\n%s" % stats.get_str())

    save_path = run_data.write_run(
        name=name,
        save_directory=save_directory
    )
    logger.info("Wrote run data to path: %s" % save_path)