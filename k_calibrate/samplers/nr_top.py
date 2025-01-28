import pandas as pd

from k_calibrate.calibrate import Sampler
from k_calibrate.files import load_file
from k_calibrate.new_relic import client_from_env_file
from k_calibrate.utils.nr import timestamp_to_datetime

# This should probably capture all reporting intervals
SINCE = "1 minute ago"

class NRTop(Sampler):
    def __init__(
        self,
        command: str,
        cluster_name: str,
        namespace: str = None
    ):
        if namespace is not None:
            raise NotImplementedError("Namespace scoping not implemented.")

        if command == 'pod':
            self.query = load_file(
                'sql/pod_top.sql',
                arguments={
                    'cluster_name': cluster_name
                },
                log_rendered=True
            )
        elif command == 'node':
            raise NotImplementedError("Not implemented for 'node' command")

        self.nr = client_from_env_file()

    def sample(self) -> pd.DataFrame:
        result = self.nr.query(self.query)

        for row in result:
            row['podName'] = row.pop('facet')
        df = pd.DataFrame(result)

        df['timestamp'] = df['timestamp'].map(timestamp_to_datetime)

        return df