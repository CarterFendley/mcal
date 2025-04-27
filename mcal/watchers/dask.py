import pandas as pd
from colorama import Fore, Style, just_fix_windows_console

from mcal.samplers.dask_k8_cluster import DaskK8Cluster
from mcal.samplers.dask_prom import DaskPromScheduler, DaskPromWorker
from mcal.utils.format import bytes_to_human_readable

from . import Watcher

just_fix_windows_console()

class DaskCluster(Watcher):
    def __init__(self):
        self.subscribe(DaskK8Cluster)

    def id_found(self, kind, id: str, record: pd.Series):
        print("New cluster: %s" % id)
        for attr in ('creation_timestamp', 'worker_replicas'):
            print(f'  {attr}: {record[attr]}')

    def id_gone(self, kind, id: str):
        print("Cluster gone: %s" % id)

    def id_returned(self, kind, id: str, record):
        print("Cluster returned: %s" % id)

class _GenericWatcher(Watcher):
    warn_changes = ()
    formatters = {}

    def __init__(self):
        self.previous_schema = None
        self.previous_data = {}

    def new_sample(self, kind, records: pd.DataFrame):
        # If there is not previous schema, do not alert changes just update
        if self.previous_schema is None:
            self.previous_schema = records.dtypes

        changes = []
        for name, dtype in records.dtypes.items():
            if name not in self.previous_schema:
                changes.append(f"New attribute: '{name}'")
                self.previous_schema[name] = dtype
            elif self.previous_schema[name] != dtype:
                changes.append(f"Dtype changes: {self.previous_schema[name]} --> {dtype}")
                self.previous_schema[name] = dtype

        if len(changes) != 0:
            print("Schema updates for sampler: %s" % kind)
            for c in changes:
                print(f"  - {c}")

    def _get_data(self, record: pd.Series) -> dict:
        data = {}
        for attr, value in record.items():
            data[attr] = value

        return data

    def _get_changes(self, id: str, record: pd.Series):
        data = self._get_data(record)

        for key, value in data.items():
            if key not in self.previous_data[id]:
                yield key, None, value
            elif self.previous_data[id][key] != value:
                yield key, self.previous_data[id][key], value

        self.previous_data[id] = data

    def id_found(self, kind, id: str, record: pd.Series):
        print("New %s id found: %s" % (kind.__name__, id))
        self.previous_data[id] = self._get_data(record)

    def id_updates(self, kind, id: str, records: pd.DataFrame):
        for _, row in records.iterrows():
            updates = self._get_changes(id, row)
            updates = list(filter(lambda u: u[0] in self.warn_changes, updates))
            if len(updates) != 0:
                print("Updates for id: %s" % id)
                for attr, old, new in updates:
                    arrow = "==>"
                    try:
                        if new < old:
                            arrow = f"{Fore.RED}{arrow}{Style.RESET_ALL}"
                        else:
                            arrow = f"{Fore.GREEN}{arrow}{Style.RESET_ALL}"
                    except TypeError:
                        pass

                    if format := self.formatters.get(attr):
                        def safe_format(value):
                            try:
                                return format(value)
                            except Exception as err:
                                print(f"Warning: unable to format '{attr}' of value: {value}")
                        old = safe_format(old)
                        new = safe_format(new)
                    print(f"  {attr}: {old} {arrow} {new}")

class DaskScheduler(_GenericWatcher):
    def __init__(self):
        super().__init__()
        self.subscribe(DaskPromScheduler)

        self.warn_changes = (
            'dask_scheduler_workers_removed_total',
            'dask_scheduler_tasks-state=erred',
            'dask_scheduler_tasks-state=no-worker'
        )

class DaskWorker(_GenericWatcher):
    def __init__(self):
        super().__init__()
        self.subscribe(DaskPromWorker)

        self.warn_changes = (
            'dask_worker_memory_bytes-type=managed',
            'dask_worker_memory_bytes-type=unmanaged',
            'dask_worker_memory_bytes-type=spilled',
            'process_virtual_memory_bytes',
            'process_resident_memory_bytes',
        )
        self.formatters = {}
        for attr in self.warn_changes:
            self.formatters[attr] = bytes_to_human_readable