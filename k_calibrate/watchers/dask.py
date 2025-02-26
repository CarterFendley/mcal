import pandas as pd

from . import Watcher


class DaskWatcher(Watcher):
    def __init__(self):
        self.known_k8_clusters = {}
        self.known_schedulers = {}

    def _handle_k8_cluster(self, sample: pd.DataFrame):
        for index, row in sample.iterrows():
            cluster_id = (row['namespace'], row['name'], row['creation_timestamp'])

            if cluster_id not in self.known_k8_clusters:
                print(f"Found new K8 cluster '{row['name']}' in namespace '{row['namespace']}'")
                self.known_k8_clusters[cluster_id] = {}

    def _handle_prom_scheduler(self, sample: pd.DataFrame):
        for index, row in sample.iterrows():
            scheduler_id = (
                row['namespace'],
                row['cluster_name'],
                row['scheduler_name'],
            )

            if scheduler_id not in self.known_schedulers:
                print(f"Found new scheduler '{row['scheduler_name']}' for cluster '{row['cluster_name']}'")

                keys = [
                    'workers_total',
                    'workers_partially_saturated',
                    'workers_saturated',
                    'tasks_total',
                    # In progress
                    'tasks_waiting',
                    'tasks_queued',
                    'tasks_processing',
                    # Finished
                    'tasks_memory',
                    'tasks_released',
                    'tasks_erred'
                ]
                self.known_schedulers[scheduler_id] = {
                    k: row[k] for k in keys
                }
                for key, value in self.known_schedulers[scheduler_id].items():
                    print(f"\t- {key}: {value}")
            else:
                diff = {}
                for key, value in self.known_schedulers[scheduler_id].items():
                    if value != row[key]:
                        diff[key] = (value, row[key])
                        self.known_schedulers[scheduler_id][key] = row[key]
                if len(diff) != 0:
                    print(f"Updates found for scheduler '{row['scheduler_name']}' for cluster '{row['cluster_name']}'")
                    for key, (previous, current) in diff.items():
                        print(f"\t- {key}: {previous} -->> {current}")


    def after_sample(self, name: str, sample: pd.DataFrame):
        if name == 'DaskK8Cluster':
            self._handle_k8_cluster(sample)
        if name == 'DaskPromScheduler':
            self._handle_prom_scheduler(sample)

