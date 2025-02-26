import pandas as pd

from mcal.calibrate import Sample, Sampler
from mcal.new_relic import client_from_env_file
from mcal.utils.nr import timestamp_to_datetime

SINCE = "1 hour ago"

class NRFrequency(Sampler):
    def __init__(self, cluster_name: str):
        self.cluster_name = cluster_name

    def sample(self) -> Sample:
        nr = client_from_env_file()
        query = f"""
        SELECT uniques(timestamp) as 'timestamp'
        FROM K8sClusterSample
        WHERE clusterName = '{self.cluster_name}'
            AND agentName = 'Infrastructure'
        SINCE {SINCE}
        ORDER BY timestamp
        """

        result = nr.query(query)
        timestamps = result[0]["timestamp"]
        # NOTE: Order by timestamp does not seem to be working, maybe since 'timestamp' is a special field?
        # Ref: https://forum.newrelic.com/s/hubtopic/aAX8W0000008aJrWAI/get-results-from-new-relic-in-sorted-order
        timestamps = sorted(timestamps)

        df = pd.DataFrame()
        df['timestamp'] = tuple(map(timestamp_to_datetime, timestamps))
        df['delta'] = df['timestamp'].diff().dt.total_seconds()

        return Sample(data=df)

    @staticmethod
    def print_data(df: pd.DataFrame):
        print(df['delta'].describe())