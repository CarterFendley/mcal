from http.client import HTTPConnection, RemoteDisconnected
from typing import Iterable, Optional

import pandas as pd
from dask_kubernetes.constants import SCHEDULER_NAME_TEMPLATE
from kubernetes import client, config
from kubernetes.stream import portforward
from kubernetes.stream.ws_client import PortForward
from prometheus_client.metrics_core import Metric
from prometheus_client.parser import text_string_to_metric_families

from mcal import Sampler
from mcal.utils.logging import LogDeduplicate
from mcal.utils.prometheus import mapper_python_info, metrics_to_pd_series

dedup = LogDeduplicate()

class PortForwardConnection(HTTPConnection):
    def __init__(self, ws_portforward: PortForward, port: int):
        super().__init__(
            host='http://localhost',
            port=port,
        )

        self.ws_portforward = ws_portforward
        self.port = port
        self._create_connection = self.__create_pf_conn

    def __create_pf_conn(self, *args, **kwargs):
        # TODO: If pods servers are not ready, this can explode as soon as a request is sent
        return self.ws_portforward.socket(self.port)

    def close(self):
        # Prevent closing of socket owned by the PortForward
        self.sock = None
        super().close()

class K8Resources:
    def __init__(self):
        config.load_kube_config()

        self.v1_api = client.CoreV1Api()
        self.cr_api = client.CustomObjectsApi()

    def find_clusters(
        self,
        find_schedulers: bool = False,
        find_workers: bool = False,
    ) -> list:
        clusters = []
        cluster_crds = self.cr_api.list_cluster_custom_object(
            # Still a little iffy on this, like how I don't specify 'DaskCluster' anywhere BUT do specify 'daskclusters' not sure what type of filter is active
            # kubectl get crd
            # kubectl describe crds daskclusters.kubernetes.dask.org | less
            group='kubernetes.dask.org',
            plural='daskclusters', 
            version='v1', # Would be nice to pull automatically
        )

        for item in cluster_crds['items']:
            if item['kind'] != 'DaskCluster':
                # TODO: Not sure if this check is need b/c confused by 'list_cluster_custom_object'
                dedup(print, f"Skipping non DaskCluster resource: {item['kind']}")
                continue
            if item['apiVersion'] != 'kubernetes.dask.org/v1':
                dedup(print, f"Skipping unrecognized apiVersion: {item['apiVersion']}")

            cluster = {
                'namespace': item['metadata']['namespace'],
                'name': item['metadata']['name'],
                'kind': 'dask-operator'
            }
            if find_schedulers:
                self.find_schedulers(cluster)
            if find_workers:
                self.find_workers(cluster)
            clusters.append(cluster)

        return clusters

    def find_schedulers(self, cluster: dict, must_be_ready: bool = True):
        """Update cluster with schedulers"""
        try:
            scheduler_service = SCHEDULER_NAME_TEMPLATE.format(cluster_name=cluster['name'])
            service = self.v1_api.read_namespaced_service(
                name=scheduler_service,
                namespace=cluster['namespace'],
            )
        except client.ApiException:
            dedup(
                print,
                f"Unable to get scheduler name '{scheduler_service}' for cluster '{cluster['name']}' in namespace '{cluster['namespace']}'"
            )
            cluster['scheduler_pods'] = []
            return


        service_selector = service.spec.selector
        service_selector = ",".join(
            [f"{k}={v}" for k, v in service_selector.items()]
        )
        pods = self.v1_api.list_namespaced_pod(
            namespace=cluster['namespace'],
            label_selector=service_selector
        )
        if must_be_ready:
            pods_list = list(filter(
                lambda item: (
                    item.status.container_statuses is not None
                    and all(status.ready for status in item.status.container_statuses)
                ),
                pods.items
            ))
        else:
            pods_list = pods.items
        pod_names = [item.metadata.name for item in pods_list]

        cluster['scheduler_pods'] = pod_names

    def find_workers(self, cluster: dict, must_be_ready: bool = True):
        # Reference: https://github.com/dask/dask-kubernetes/blob/547c911efc58fa003d4cb8d49fcd58a7536fa7e7/dask_kubernetes/operator/controller/controller.py#L145-L150
        selector = ",".join((
            f"dask.org/cluster-name={cluster['name']}",
            "dask.org/component=worker",
            # TODO: Worker group name?
        ))

        pods = self.v1_api.list_namespaced_pod(
            namespace=cluster['namespace'],
            label_selector=selector
        )

        if must_be_ready:
            pods_list = list(filter(
                lambda item: (
                    item.status.container_statuses is not None
                    and all(status.ready for status in item.status.container_statuses)
                ),
                pods.items
            ))
        else:
            pods_list = pods.items
        pod_names = [item.metadata.name for item in pods_list]

        cluster['worker_pods'] = pod_names

    def get_conn(self, namespace: str, pod_name: str, port: int) -> PortForwardConnection:
        pf: PortForward = portforward(
            api_method=self.v1_api.connect_get_namespaced_pod_portforward,
            namespace=namespace,
            name=pod_name,
            ports=f'{port}' # Has to be a string for the kubernetes client's implementation
        )

        conn = PortForwardConnection(
            ws_portforward=pf,
            port=port
        )
        return conn

    def pod_prom_sample(
        self,
        namespace: str,
        pod: str,
        port: int,
        endpoint: str = '/metrics',
        write_rsp: bool = False
    ) -> Optional[Iterable[Metric]]:
        # TODO(20): Leave connection open?
        conn = self.get_conn(
            namespace=namespace,
            pod_name=pod,
            port=port
        )
        conn.request('GET', endpoint)
        try:
            rsp = conn.getresponse().read().decode()
        except RemoteDisconnected:
            dedup(print, "WARNING: Pod disconnected before sending response: %s" % pod)
            return None

        # TODO: Combine these
        conn.ws_portforward.close()
        conn.close()

        # TODO: This is dask (not prom) specific
        if rsp.startswith("# Prometheus metrics are not available"):
            dedup(print, "WARNING: Prometheus is not enabled on scheduler: %s" % pod)

            return None


        if write_rsp:
            with open(":".join((namespace, pod)) + '.txt', 'w') as f:
                f.write(rsp)

        return text_string_to_metric_families(rsp)

class DaskPromScheduler(Sampler):
    def __init__(self, discovery: str = 'k8'):
        if discovery == 'k8':
            self.resources = K8Resources()
        else:
            raise NotImplementedError(f"Dask cluster discovery method not implemented: {discovery}")

    def sample(self) -> pd.DataFrame:
        # TODO(20): Use watch api for this stuff? 
        clusters = self.resources.find_clusters(find_schedulers=True)

        data = []
        for cluster in clusters:
            cluster_info = pd.Series()
            cluster_info['id'] = f"{cluster['namespace']}/{cluster['name']}"
            cluster_info['namespace'] = cluster['namespace']
            cluster_info['cluster_name'] = cluster['name']
            cluster_info['kind'] = cluster['kind']

            num_schedulers = len(cluster['scheduler_pods'])
            if num_schedulers == 0:
                # Bail out, nothing to read
                continue
            elif num_schedulers != 1:
                raise RuntimeError("Only implemented for one scheduler pod not: %s" % num_schedulers)

            scheduler_pod = cluster['scheduler_pods'][0]
            cluster_info['scheduler_name'] = scheduler_pod
            families = self.resources.pod_prom_sample(
                namespace=cluster['namespace'],
                pod=scheduler_pod,
                port=8787
            )
            if families is not None:
                cluster_info = pd.concat([
                    cluster_info,
                    metrics_to_pd_series(
                        families,
                        custom_maps={
                            'python_info': mapper_python_info
                        }
                    )
                ])

            data.append(cluster_info)

        return pd.DataFrame(data)

class DaskPromWorker(Sampler):
    def __init__(self, discovery: str = 'k8'):
        if discovery == 'k8':
            self.resources = K8Resources()
        else:
            raise NotImplementedError(f"Dask cluster discovery method not implemented: {discovery}")

    def sample(self):
        # TODO(20): Use watch api for this stuff? 
        clusters = self.resources.find_clusters(find_workers=True)

        data = []
        for cluster in clusters:
            for worker_pod in cluster['worker_pods']:
                worker_info = pd.Series()
                worker_info['id'] = f"{cluster['namespace']}/{cluster['name']}/{worker_pod}"
                worker_info['namespace'] = cluster['namespace']
                worker_info['cluster_name'] = cluster['name']

                families = self.resources.pod_prom_sample(
                    namespace=cluster['namespace'],
                    pod=worker_pod,
                    port=8788,
                    # write_rsp=True
                )
                if families is not None:
                    worker_info = pd.concat([
                    worker_info,
                    metrics_to_pd_series(
                        families,
                        custom_maps={
                            'python_info': mapper_python_info
                        }
                    )
                ])

                data.append(worker_info)

        return pd.DataFrame(data)