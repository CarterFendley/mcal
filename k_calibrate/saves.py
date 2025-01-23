import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

import pandas as pd

from k_calibrate.config import KCConfig, load_config_file
from k_calibrate.utils.logging import get_logger

# NOTE: I think it is important that %Z is included to assure UTC
DATE_FORMAT = "%Y-%m-%d_%H:%M:%S_%Z"

logger = get_logger(__name__)

@dataclass
class SampleRun:
    start_time: datetime
    config: KCConfig
    sample_data: Dict[str, pd.DataFrame] = field(default_factory=lambda: {})

    def gen_name(self) -> str:
        return self.start_time.strftime(DATE_FORMAT)

    def write_run(
        self,
        name: Optional[str] = None,
        data_type: str = 'csv'
    ) -> str:
        if name is None:
            name = self.gen_name()

        folder_path = os.path.join('kc_run_data', name)
        if os.path.exists(folder_path):
            # TODO: Remove this, really bad to error if run has data
            raise RuntimeError("Write path already exists: %s", folder_path)

        os.makedirs(folder_path)
        logger.info("Writing sample run to directory: %s" % folder_path)

        config_path = os.path.join(folder_path, "config.yml")
        self.config.save(config_path)

        for sample_name, sample in self.sample_data.items():
            if data_type == 'csv':
                path = os.path.join(folder_path, sample_name + ".csv")
                sample.to_csv(path, header=True)
            else:
                raise NotImplementedError("Run saving not implemented for type: %s" % data_type)

        return folder_path

def load_run(path: str) -> SampleRun:
    try:
        folder_name = os.path.basename(path)
        start_time = datetime.strptime(folder_name, DATE_FORMAT)
    except ValueError:
        start_time = None

    config = None
    sample_data = {}
    for file in os.listdir(path):
        file_path = os.path.join(path, file)
        if file == "config.yml":
            config = load_config_file(file_path)
            continue

        name, ext = os.path.splitext(file)

        if ext == "csv":
            sample_data[name] = pd.read_csv(file_path)
        else:
            raise NotImplementedError("Found unexpected type in save folder: %s" % ext)

    if config is None:
        # TODO: Definitely can optimize this if data load times get larger
        raise RuntimeError("Unable to find 'config.yml' file in directory: %s" % path)
    if len(sample_data) == 0:
        logger.warning("Not sample data was found in directory, returning a sample run with empty data: %s" % path)

    return SampleRun(
        start_time=start_time,
        config=config,
        sample_data=sample_data
    )