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
        self.data = {}

    def _get_data(self, record: pd.Series):
        data = {}
        for attr in self.warn_changes:
            if attr in record:
                data[attr] = record[attr]

        return data

    def _get_changed(self, id: str, record: pd.Series):
        data = self._get_data(record)
        for key, value in data.items():
            # print(key, value)
            if key not in self.data[id]:
                print("NEW KEY __--------!")
                yield key, None, value
            elif self.data[id][key] != value:
                yield key, self.data[id][key], value

        self.data[id] = data

    def id_found(self, kind, id: str, record: pd.Series):
        print("New %s id found: %s" % (kind, id))
        self.data[id] = self._get_data(record)

    def id_updates(self, kind, id: str, records: pd.DataFrame):
        for _, row in records.iterrows():
            updates = list(self._get_changed(id, row))
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
                        old = format(old)
                        new = format(new)
                    print(f"  {attr}: {old} {arrow} {new}")

class DaskScheduler(_GenericWatcher):
    def __init__(self):
        super().__init__()
        self.subscribe(DaskPromScheduler)

        self.warn_changes = (
            'workers_removed_total',
            'tasks_erred',
            'tasks_no-worker'
        )

class DaskWorker(_GenericWatcher):
    def __init__(self):
        super().__init__()
        self.subscribe(DaskPromWorker)

        self.warn_changes = (
            'memory_total',
            'memory_managed',
            'memory_unmanaged',
            'memory_spilled',
            'process_virtual_memory',
            'process_resident_memory',
        )
        self.formatters = {}
        for attr in self.warn_changes:
            self.formatters[attr] = bytes_to_human_readable