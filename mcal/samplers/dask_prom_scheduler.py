from http.client import HTTPConnection

import pandas as pd
from dask_kubernetes.constants import SCHEDULER_NAME_TEMPLATE
from kubernetes import client, config
from kubernetes.stream import portforward
from kubernetes.stream.ws_client import PortForward
from prometheus_client.parser import text_string_to_metric_families

from mcal.calibrate import Sampler


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
        find_schedulers: bool = True
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
                print(f"Skipping non DaskCluster resource: {item['kind']}")
                continue
            if item['apiVersion'] != 'kubernetes.dask.org/v1':
                print(f"Skipping unrecognized apiVersion: {item['apiVersion']}")

            cluster = {
                'namespace': item['metadata']['namespace'],
                'name': item['metadata']['name'],
                'kind': 'dask-operator'
            }
            if find_schedulers:
                self.find_schedulers(cluster)
            clusters.append(cluster)

        return clusters

    def find_schedulers(self, cluster: dict, must_be_ready: bool = True):
        """Update cluster with schedulers"""
        service = self.v1_api.read_namespaced_service(
            name=SCHEDULER_NAME_TEMPLATE.format(cluster_name=cluster['name']),
            namespace=cluster['namespace'],
        )
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
            pod_list = pods.items
        pod_names = [item.metadata.name for item in pods_list]

        cluster['scheduler_pods'] = pod_names

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

class DaskPromScheduler(Sampler):
    def __init__(self, discovery: str = 'k8'):
        if discovery == 'k8':
            self.resources = K8Resources()
        else:
            raise NotImplementedError(f"Dask cluster discovery method not implemented: {discovery}")

    def sample(self) -> pd.DataFrame:
        clusters = self.resources.find_clusters()

        data = []
        for cluster in clusters:
            cluster_info = {}
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
            conn = self.resources.get_conn(
                namespace=cluster['namespace'],
                pod_name=scheduler_pod,
                port=8787 # Dask dashboard port
            )
            conn.request('GET', '/metrics')
            rsp = conn.getresponse().read().decode()
            if rsp.startswith("# Prometheus metrics are not available"):
                print("WARNING: Prometheus is not enabled on scheduler: %s" % scheduler_pod)
            else:
                families = text_string_to_metric_families(rsp)
                # https://distributed.dask.org/en/latest/prometheus.html
                for family in families:
                    if family.name == 'dask_scheduler_workers':
                        worker_info = {}
                        total = 0
                        for sample in family.samples:
                            state = sample.labels['state']
                            worker_info[f'workers_{state}'] = sample.value
                            total += sample.value

                        # This is just to order 'workers_total' first
                        cluster_info['workers_total'] = total
                        cluster_info.update(worker_info)
                    if family.name == 'dask_scheduler_tasks':
                        task_info = {}
                        total = 0
                        for sample in family.samples:
                            state = sample.labels['state']
                            task_info[f'tasks_{state}'] = sample.value
                            total += sample.value

                        # This is just to order 'tasks_total' first
                        cluster_info['tasks_total'] = total
                        cluster_info.update(task_info)

            # TODO: Combine these
            conn.ws_portforward.close()
            conn.close()

            data.append(cluster_info)

        return pd.DataFrame(data)