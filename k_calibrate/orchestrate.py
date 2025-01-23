from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd

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

def run(config: KCConfig):
    schedule, samplers, stop_criteria = config.create()

    # Go ahead and allocate run data
    run_data = SampleRun(
        start_time=utc_now(),
        config=config
    )
    for name in samplers.keys():
        run_data.sample_data[name] = pd.DataFrame()

    # TODO:
    # 1. Multiple samplers in different threads / processes
    # 2. Passive samplers without schedule
    stats = RunStats()
    while not stop_criteria(stats):
        schedule.sleep()
        logger.info("Iteration: %s", stats.iterations + 1)
        for name, sampler in samplers.items():
            sample_time = utc_now()
            sample = sampler.sample()

            if sample.timestamp is None:
                sample.timestamp = sample_time

            # Store new row
            run_data.sample_data[name] = pd.concat(
                [
                    run_data.sample_data[name],
                    pd.DataFrame(sample.as_pandas_row()),
                ],
                ignore_index=True # Not 100% on this
            )

        stats.iterations += 1
        stats.time_elapsed = utc_now() - run_data.start_time

    logger.info("Run ended successfully:\n%s" % stats.get_str())

    save_path = run_data.write_run()
    logger.info("Wrote run data to path: %s" % save_path)