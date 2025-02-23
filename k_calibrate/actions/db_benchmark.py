# import os
# import sys

# assert 'DB_BENCHMARK_DIR' in os.environ, "Since db-bechmark is not provided as a packages, a 'DB_BENCHMARK_DIR' directory must be specified to locate it"
# dask_db_benchmark = os.path.join(
#     os.path.abspath(os.environ['DB_BENCHMARK_DIR']),
#     'dask'
# )
# assert os.path.isdir(dask_db_benchmark), "Dask db-benchmark directory not found: %s" % dask_db_benchmark
# sys.path.append(dask_db_benchmark)

# from common import QueryRunner
# from join_dask import (
#     QueryOne,
#     QueryTwo,
#     QueryThree,
#     QueryFour,
#     QueryFive,
# )

from dask.distributed import Client
from dask_kubernetes.operator import KubeCluster


def dask_client(n_workers: int = 2) -> Client:
    print("Creating cluster...")
    cluster = KubeCluster(
        name="my-kubernetes-cluster",
        n_workers=2,
        # Needed for metrics server to be enabled
        env={"EXTRA_PIP_PACKAGES": "prometheus-client"}
    )
    # cluster = KubeCluster()

    # print(f"Scaling cluster (n_workers={n_workers})...")
    # cluster.scale(n=n_workers)

    return Client(cluster)

def run():
    dask_client()

    print("Sleeping")
    import time
    time.sleep(1200)

# export DB_BENCHMARK_DIR="/Users/carter/src/db-benchmark"
# python3 k_calibrate/actions/db_benchmark.py
# Note: Some issue with my python=3.13 install, revert to 3.10 worked (maybe reinstall would have worked)
if __name__ == '__main__':
    run()