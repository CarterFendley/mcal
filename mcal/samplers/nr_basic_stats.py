import pandas as pd

from mcal.calibrate import Sample, Sampler
from mcal.files import load_file
from mcal.new_relic import client_from_env_file

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
        query = load_file(
            file='sql/containers_running.sql',
            arguments={
                'clusterName': self.cluster_name,
                'namespaceName': self.namespace,
                'status': 'Waiting',
                'since': "1 minute ago"
            },
            log_rendered=True
        )
        result = nr.query(query)

        return Sample(data_points={
            'num_containers': len(result)
        })