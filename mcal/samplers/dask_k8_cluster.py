import pandas as pd
from kubernetes import client, config

from mcal.calibrate import Sampler


class DaskK8Cluster(Sampler):
    def __init__(self):
        config.load_kube_config()

        self.v1_api = client.CoreV1Api()
        self.api_client = client.ApiClient() 
        self.cr_api = client.CustomObjectsApi(self.api_client) # NOTE: CoreV1Api does not have 'client_size_validation'

    def sample(self) -> pd.DataFrame:
        # Make all requests as close in time as possible
        cluster_crds = self.cr_api.list_cluster_custom_object(
            # Still a little iffy on this, like how I don't specify 'DaskCluster' anywhere BUT do specify 'daskclusters' not sure what type of filter is active
            # kubectl get crd
            # kubectl describe crds daskclusters.kubernetes.dask.org | less
            group='kubernetes.dask.org',
            plural='daskclusters', 
            version='v1', # Would be nice to pull automatically
        )
        workergroup_crds = self.cr_api.list_cluster_custom_object(
            group='kubernetes.dask.org',
            plural='daskworkergroups', 
            version='v1', # Would be nice to pull automatically
        )

        # -------------------------
        # Organize collected data -
        # -------------------------
        # First sort worker groups by namespace / cluster name
        workergroups = {}
        for item in workergroup_crds['items']:
            if item['kind'] != 'DaskWorkerGroup':
                # TODO: Not sure if this check is need b/c confused by 'list_cluster_custom_object'
                print(f"Skipping non DaskWorkerGroup resource: {item['kind']}")
                continue
            if item['apiVersion'] != 'kubernetes.dask.org/v1':
                print(f"Skipping unrecognized apiVersion: {item['apiVersion']}")

            metadata = item['metadata']
            workergroups[(metadata['namespace'], item['spec']['cluster'])] = item

        data = []
        for item in cluster_crds['items']:
            cluster_info = {}
            if item['kind'] != 'DaskCluster':
                # TODO: Not sure if this check is need b/c confused by 'list_cluster_custom_object'
                print(f"Skipping non DaskCluster resource: {item['kind']}")
                continue
            if item['apiVersion'] != 'kubernetes.dask.org/v1':
                print(f"Skipping unrecognized apiVersion: {item['apiVersion']}")
            metadata = item['metadata']
            namespace = metadata['namespace']
            name = metadata['name']
            cluster_info['namespace'] = namespace 
            cluster_info['name'] = name
            cluster_info['kind'] = 'dask-operator'
            cluster_info['creation_timestamp'] = metadata['creationTimestamp']

            wg_info = workergroups.get((namespace, name))
            # TODO: DaskCluster.spec.worker.replicas also exists
            # - How do these work with the wg replicas?
            # - wg is at 2 with cluster.scale(...) and cluster at zero (two pods spawned)
            # - Documentation lists both as "number of worksers to spawn": https://kubernetes.dask.org/en/latest/operator_resources.html
            # - Looks like `DaskCluster` updates will be reflected in `DaskWorkerGroup` but not the opposite, can control from `DaskCluster` but `DaskWorkerGroup` will reflect most accurate
            # - Changes pulled from here: https://github.com/dask/dask-kubernetes/blob/main/dask_kubernetes/operator/controller/controller.py#L629-L630
            if wg_info is None:
                cluster_info['worker_replicas'] = None
            else:
                cluster_info['worker_replicas'] = wg_info['spec']['worker']['replicas']

            data.append(cluster_info)

        return pd.DataFrame(data)