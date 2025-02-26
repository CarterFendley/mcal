from typing import Any, Dict, Iterable, List, Optional, Union

import pandas as pd

from mcal.runner.models import CalibrationRun
from mcal.utils.logging import get_logger

logger = get_logger(__name__)

class Compare:
    def __init__(
        self,
        run: CalibrationRun,
        iterate_by: Optional[List[str]] = None
    ):
        self.run = run
        self.iterate_by = iterate_by

    def yield_data(self) -> Iterable[Dict[str, pd.DataFrame]]:
        if self.iterate_by is None:
            yield self.run.collected_data
        else:
            already_yielded = pd.DataFrame(columns=self.iterate_by)
            for dataset in self.run.collected_data.values():
                uniques = dataset[self.iterate_by].drop_duplicates()
                new = (
                    uniques.merge(already_yielded, how='outer', indicator=True)
                    .query('_merge=="left_only"')
                    .drop('_merge', axis=1)
                )

                for _, row in new.iterrows():
                    row_df = row.to_frame().T
                    to_yield = {}
                    # NOTE: Overriding 'dataset' here, don't need outer loop value anymore
                    for dataset_name, dataset in self.run.collected_data.items():
                        to_yield[dataset_name] = dataset.merge(
                            row_df,
                            how='inner',
                            on=row_df.columns.to_list(),
                        )
                    yield to_yield

                # Add already yielded for next loop
                already_yielded = pd.concat([already_yielded, new])

def respond_to_event(
    name: str,
    config: Dict[str, Any],
    msg: Union[List[str], str]
):
    if isinstance(msg, str):
        msg = [msg]
    action = config.get(name, 'warn')
    if action not in ('error', 'warn'):
        logger.info("Invalid action '%s' for event '%s', defaulting to 'warn'." % (action, name))
        action = 'warn'

    if action == 'error':
        for m in msg:
            logger.error(m)
        raise RuntimeError("Error: '%s'" % name)
    elif action == 'warn':
        for m in msg:
            logger.warning(m)

def filter_timestamps(
    generator: Iterable[Dict[str, pd.DataFrame]],
    tolerance: float=1.0,
    config: Dict[str, Any] = None
) -> Iterable[Dict[str, pd.DataFrame]]:
    if config is None:
        config = {}

    while True:
        try:
            # TODO: Is there access to the `SupportsNext` protocol??
            datasets: Dict[str, pd.DataFrame] = next(generator)
        except StopIteration:
            break

        # Filter duplicates, check amount of unique timestamps
        for name, dataset in datasets.items():
            dataset = dataset.drop_duplicates()

            unique_timestamps = dataset['timestamp'].drop_duplicates().shape[0]
            if unique_timestamps != dataset.shape[0]:
                respond_to_event(
                    name='duplicate_timestamps',
                    config=config,
                    msg=[
                        "Number of unique timestamps does not equal the number of unique records, this may indicate that the timestamp is not full indicative of all data collection periods. (dataset=%s, unique_timestamps=%s, unique_records=%s)" % (name, unique_timestamps, dataset.shape[0]),
                        "Maybe you need an 'iterate_by' condition on your Compare instance?"
                    ]
                )

            datasets[name] = dataset
