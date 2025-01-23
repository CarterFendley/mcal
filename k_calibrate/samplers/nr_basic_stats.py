import pandas as pd

from k_calibrate.calibrate import Sample, Sampler
from k_calibrate.new_relic import client_from_env_file
from k_calibrate.sql import load_sql
from k_calibrate.utils.nr import timestamp_to_datetime

SINCE = "1 hour ago"

class NRBasicStats(Sampler):
    def __init__(
        self,
        cluster_name: str,
        namespace: str
    ):
        self.cluster_name = cluster_name
        self.namespace = namespace

    def sample(self) -> Sample:
        nr = client_from_env_file()
        query = load_sql(
            file='containers_running.sql',
            arguments={
                'clusterName': self.cluster_name,
                'namespaceName': self.namespace,
                'status': 'Waiting',
                'since': "1 minute ago"
            }
        )
        result = nr.query(query)

        return Sample(data_points={
            'num_containers': len(result)
        })