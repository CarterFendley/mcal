from k_calibrate.calibrate import Sample, Sampler
from k_calibrate.new_relic import NewRelicClient

SINCE = "1 hour ago"

class NewRelicNamespaceSampler(Sample):
    def __init__(self, cluster_name: str):
        self.cluster_name = cluster_name

    def sample(self):
        query = f"""
        """