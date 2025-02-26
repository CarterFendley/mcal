import os
import sys

assert 'DB_BENCHMARK_DIR' in os.environ, "Since db-bechmark is not provided as a packages, a 'DB_BENCHMARK_DIR' directory must be specified to locate it"
DB_BENCHMARK_DIR = os.path.abspath(os.environ['DB_BENCHMARK_DIR'])
dask_db_benchmark = os.path.join(DB_BENCHMARK_DIR, 'dask')
DATA_DIR = os.path.join(DB_BENCHMARK_DIR, 'data')
G1_SMALL = os.path.join(DATA_DIR, 'G1_1e7_1e2_0_0.csv')
assert os.path.isdir(dask_db_benchmark), "Dask db-benchmark directory not found: %s" % dask_db_benchmark
sys.path.append(dask_db_benchmark)

from dask.distributed import Client
from dask_kubernetes.operator import KubeCluster

from mcal.actions import Action
from mcal.runner.models import RunStats

from common import QueryRunner # isort:skip
from join_dask import ( # isort:skip
    QueryOne,
    QueryTwo,
    QueryThree,
    QueryFour,
    QueryFive,
)


class DBBenchmark(Action):
    AWAIT_AFTER_ITER = False

    def __init__(self, n_workers: int = 2):
        self.n_workers = n_workers

    def after_iter(self, stats: RunStats):
        # Only run once
        if stats.iterations == 0:
            self.run(no_dask_output=True)

    def dask_client(self, no_dask_output: bool) -> Client:
        print("Creating cluster...")
        cluster = KubeCluster(
            # name="my-kubernetes-cluster", # Sometimes nice to have deterministic name
            n_workers=self.n_workers,
            # Dask's pretty display fucks up other async output
            quiet=no_dask_output,
            # Needed for metrics server to be enabled
            env={"EXTRA_PIP_PACKAGES": "prometheus-client"}
        )

        client = Client(cluster)
        print("Waiting for workers...")
        client.wait_for_workers(self.n_workers)
        return client

    def run_group_by_task(self, client: Client):
        assert os.path.isfile(G1_SMALL)

        print("Uploading data to workers: %s" % G1_SMALL)
        client.upload_file(G1_SMALL)

    def run(self, no_dask_output: bool = False):
        self.client = self.dask_client(no_dask_output)
        self.run_group_by_task(self.client)
        print("Sleeping")
        import time
        time.sleep(1)
        # time.sleep(1200)


# export DB_BENCHMARK_DIR="/Users/carter/src/db-benchmark"
# python3 mcal/actions/db_benchmark.py
# OR
# export DB_BENCHMARK_DIR="/Users/carter/src/db-benchmark"
# mcal run configs/db_benchmark.yml
# Note: Some issue with my python=3.13 install, revert to 3.10 worked (maybe reinstall would have worked)
if __name__ == '__main__':
    action = DBBenchmark()
    action.run()