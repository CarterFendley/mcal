import dask.dataframe as dd
import pandas as pd
from dask.distributed import Client
from dask_kubernetes.operator import KubeCluster

from mcal.actions import Action
from mcal.runner.models import RunStats

# from gcsfs import GCSFileSystem

class TaxiCab(Action):
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
            env={"EXTRA_PIP_PACKAGES": "prometheus-client gcsfs",},
        )

        client = Client(cluster)
        print("Waiting for workers...")
        client.wait_for_workers(self.n_workers)
        return client

    def run_taxi_cab(self, client: Client):
        # Reference: https://github.com/dask/dask-docker/blob/main/notebook/examples/05-nyc-taxi.ipynb

        # Read data
        print("Reading remote data...")
        df: dd.DataFrame = dd.read_csv(
            'gcs://anaconda-public-data/nyc-taxi/csv/2015/yellow_*.csv',
            storage_options={'token': 'anon'}, 
            parse_dates=['tpep_pickup_datetime', 'tpep_dropoff_datetime']
        )
        df = df.persist()
        print("df: ", df)
        print("dtypes: ", df.dtypes)
        print("Head")
        print(df.head())

        print("Df length...")
        print(len(df))


    def run(self, no_dask_output: bool = False):
        self.client = self.dask_client(no_dask_output)
        self.run_taxi_cab(self.client)
        print("Sleeping")
        import time
        time.sleep(1)
        # time.sleep(1200)


# python3 mcal/actions/dask_taxi_cab.py
# OR
# mcal run configs/db_benchmark.yml
if __name__ == '__main__':
    action = TaxiCab()
    action.run()