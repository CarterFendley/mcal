from mcal.calibrate import Sample, Sampler
from mcal.new_relic import NewRelicClient

SINCE = "1 hour ago"

class NewRelicNamespaceSampler(Sample):
    def __init__(self, cluster_name: str):
        self.cluster_name = cluster_name

    def sample(self):
        query = f"""
        """