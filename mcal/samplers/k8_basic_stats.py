from kubernetes import client, config

from mcal.calibrate import Sample, Sampler


class K8BasicStats(Sampler):
    def __init__(self, namespace: str):
        self.namespace = namespace

        config.load_kube_config()
        self.client = client.CoreV1Api()

    def sample(self) -> Sample:
        num_nodes = len(self.client.list_node().items)

        pod_list = self.client.list_namespaced_pod(self.namespace)
        num_pods = len(pod_list.items)
        num_containers = sum(map(lambda p: len(p.spec.containers), pod_list.items))

        return Sample(
            data_points={
                'num_nodes': num_nodes,
                'num_pods': num_pods,
                'num_containers': num_containers
            }
        )
