import os
import sys

import dask.bytes
import dask.dataframe
import dask.distributed

assert 'DB_BENCHMARK_DIR' in os.environ, "Since db-bechmark is not provided as a packages, a 'DB_BENCHMARK_DIR' directory must be specified to locate it"
DB_BENCHMARK_DIR = os.path.abspath(os.environ['DB_BENCHMARK_DIR'])
dask_db_benchmark = os.path.join(DB_BENCHMARK_DIR, 'dask')
# DATA_DIR = os.path.join(DB_BENCHMARK_DIR, 'data')
# G1_SMALL = os.path.join(DATA_DIR, 'G1_1e7_1e2_0_0.csv')
assert os.path.isdir(dask_db_benchmark), "Dask db-benchmark directory not found: %s" % dask_db_benchmark
sys.path.append(dask_db_benchmark)

import dask
from dask.distributed import Client, default_client
from dask_kubernetes.operator import KubeCluster, make_cluster_spec

from mcal.actions import Action
from mcal.runner.models import RunStats

import groupby_dask as groupby # isort:skip
import join_dask as join # isort:skip
from common import QueryRunner # isort:skip

ON_DISK = False
MACHINE_TYPE = 'dask-kubernetes'

class PVCluster(KubeCluster):
    """ This is a hacky way to try to offload the work of generation the bulk of `custom_cluster_spec` to KubeCluster... because otherwise doing so would be painful and error prone.

    Still have to do some match the parameters passed to `make_cluster_spec` :(
    """
    def __init__(self, pvcs: dict = None, *args, **kwargs):
        self.pvcs = pvcs
        super().__init__(*args, **kwargs)

    async def _create_cluster(self):
        if self.pvcs is None:
            return await super()._create_cluster()

        # TODO: Fix this brittle part
        spec = make_cluster_spec(
            name=self.name,
            env=self.env,
            resources=self.resources,
            worker_command=self.worker_command,
            n_workers=self.n_workers,
            image=self.image,
            scheduler_service_type=self.scheduler_service_type,
            idle_timeout=self.idle_timeout,
            jupyter=self.jupyter,
        )

        # Create upsert dict
        # https://github.com/dask/dask-kubernetes/blob/883f88943f41cff9cfb98ebc20fabbf3e32b3148/dask_kubernetes/operator/kubecluster/kubecluster.py#L862

        scheduler_pod = spec["spec"]["scheduler"]["spec"]
        worker_pod = spec["spec"]["worker"]["spec"]
        for pod in (scheduler_pod, worker_pod):
            if 'volumes' not in pod:
                pod['volumes'] = []
            container = pod["containers"][0]
            if 'volumeMounts' not in container:
                container['volumeMounts'] = []
            for name, mount in self.pvcs.items():
                pod['volumes'].append(
                    {
                        'name': name,
                        'persistentVolumeClaim': {
                            'claimName': name
                        }
                    }
                )
                container['volumeMounts'].append(
                    {
                        'mountPath': mount,
                        'name': name
                    }
                )
        self._custom_cluster_spec = spec
        return await super()._create_cluster()

class DBBenchmark(Action):
    AWAIT_AFTER_ITER = False

    def __init__(self, n_workers: int = 2):
        self.n_workers = n_workers

    def after_iter(self, stats: RunStats):
        # Only run once
        if stats.iterations == 0:
            self.run(no_dask_output=True)

    def dask_client(
        self,
        no_dask_output: bool,
        pvcs: dict = None,
    ) -> Client:
        print("Creating cluster...")
        cluster = PVCluster(
            # name="my-kubernetes-cluster", # Sometimes nice to have deterministic name
            n_workers=self.n_workers,
            # Dask's pretty display fucks up other async output
            quiet=no_dask_output,
            # Needed for metrics server to be enabled
            env={"EXTRA_PIP_PACKAGES": "prometheus-client"},
            # Custom!
            pvcs=pvcs
        )

        # print("Default client:", default_client())
        client = Client(cluster)
        info = {
            'dask.__version__': dask.__version__,
            'dask.distributed.__version': dask.distributed.__version__,
            'default_client()': default_client(),
            'scheduler': dask.config.get('scheduler'),
            # 'client': dask.config.get('client')
        }
        for name, value in info.items():
            print(f"{name} - {value}")
        print("Waiting for workers...")
        client.wait_for_workers(self.n_workers)
        return client


    def run_group_by_task(self, client: Client, data_name: str):
        filepath = os.path.join(
            '/pvc-vol',
            data_name + '.csv'
        )
        if False:
            import glob
            files = client.gather(client.submit(glob.glob, '/pvc-vol/*.csv'))
            print(files)
            dask.dataframe.read_csv(files)
        if False:
            # Same as not having it
            # https://docs.dask.org/en/stable/how-to/connect-to-remote-data.html
            # "This is the default back-end, and the one used if no protocol is passed at all."
            dask.dataframe.read_csv("file://" + filepath)
        if False:
            dask.bytes.read_bytes(filepath)
        if False:
            dask.dataframe.read_csv("dask://" + filepath)
        if False:
            dask.bytes.read_bytes(
                "dask://" + filepath,
                target_protocol="file"
            )
        if False:
            dask.dataframe.read_csv(
                "dask://" + filepath,
                storage_options={
                    "target_protocol": "file"
                }
            )
        # pass
        runner = QueryRunner(
            task="groupby",
            solution="dask",
            solution_version=dask.__version__,
            solution_revision=dask.__git_revision__,
            fun=".groupby",
            cache="FALSE",
            on_disk=ON_DISK
        )

        x = groupby.load_dataset(
            data_name=data_name,
            on_disk=ON_DISK,
            data_dir='dask:///pvc-vol',
            storage_options={
                'target_protocol': "file"
            }
        )
        in_rows = len(x)
        print(f"Input dataset rows: {in_rows:,}")

        print("Grouping...")
        runner.run_query(
            data_name=data_name,
            in_rows=in_rows,
            args=[x],
            query=groupby.QueryOne,
            machine_type=MACHINE_TYPE
        )

        print("Grouping done!")

    def run_join_task(self, client: Client, data_name: str):
            runner = QueryRunner(
                task="join",
                solution="dask",
                solution_version=dask.__version__,
                solution_revision=dask.__git_revision__,
                fun=".join",
                cache="FALSE",
                on_disk=ON_DISK
            )

            x, small, medium, big = join.load_datasets(
                data_name=data_name,
                on_disk=ON_DISK,
                data_dir='dask:///pvc-vol',
                storage_options={
                    'target_protocol': "file"
                }
            )
            in_rows = len(x)
            print(f"X dataset rows: {in_rows:,}")
            print(f"Small dataset rows: {len(small.index):,}")
            print(f"Medium dataset rows: {len(medium.index):,}")
            print(f"Big dataset rows: {len(big.index):,}")

            print("Joining...")
            print("join.QueryOne")
            runner.run_query(
                data_name=data_name,
                in_rows=in_rows,
                args=[x, small, medium, big],
                query=join.QueryOne,
                machine_type=MACHINE_TYPE
            )

            print("join.QueryTwo")
            runner.run_query(
                data_name=data_name,
                in_rows=in_rows,
                args=[x, small, medium, big],
                query=join.QueryTwo,
                machine_type=MACHINE_TYPE
            )

            print("join.QueryThree")
            runner.run_query(
                data_name=data_name,
                in_rows=in_rows,
                args=[x, small, medium, big],
                query=join.QueryThree,
                machine_type=MACHINE_TYPE
            )

            print("join.QueryFour")
            runner.run_query(
                data_name=data_name,
                in_rows=in_rows,
                args=[x, small, medium, big],
                query=join.QueryFour,
                machine_type=MACHINE_TYPE
            )

            print("join.QueryFive")
            runner.run_query(
                data_name=data_name,
                in_rows=in_rows,
                args=[x, small, medium, big],
                query=join.QueryFive,
                machine_type=MACHINE_TYPE
            )

            print("Joining done!")



    def run(self, no_dask_output: bool = False):
        self.client = self.dask_client(
            no_dask_output,
            pvcs={
                'pvc-vol': '/pvc-vol/'
            }
        )
        self.run_group_by_task(self.client, 'G1_1e7_1e2_0_0')
        self.run_join_task(self.client, 'J1_1e7_1e7_0_0')
        print("Sleeping")
        import time
        time.sleep(500)
        # time.sleep(1200)

# 0.5G dataset copy
# mcal dev pvc cp ~/src/db-benchmark/data/G1_1e7_1e2_0_0.csv pvc/pvc-vol:/pvc-vol
# mcal dev pvc cp ~/src/db-benchmark/data/J1_1e7_NA_0_0.csv pvc/pvc-vol:/pvc-vol
# mcal dev pvc cp ~/src/db-benchmark/data/J1_1e7_1e7_0_0.csv pvc/pvc-vol:/pvc-vol
# mcal dev pvc cp ~/src/db-benchmark/data/J1_1e7_1e4_0_0.csv pvc/pvc-vol:/pvc-vol
# mcal dev pvc cp ~/src/db-benchmark/data/J1_1e7_1e1_0_0.csv pvc/pvc-vol:/pvc-vol

# export DB_BENCHMARK_DIR="/Users/carter/src/db-benchmark"
# python3 mcal/actions/db_benchmark.py
# OR
# export DB_BENCHMARK_DIR="/Users/carter/src/db-benchmark"
# mcal run configs/db_benchmark.yml
# Note: Some issue with my python=3.13 install, revert to 3.10 worked (maybe reinstall would have worked)
if __name__ == '__main__':
    action = DBBenchmark()
    action.run()