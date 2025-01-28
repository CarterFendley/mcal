from .dummy import _DummyFileCount, _DummySampler
from .kubectl_top import KubectlTop
# from .k8_basic_stats import K8BasicStats
from .nr_top import NRTop

# from .nr_basic_stats import NRBasicStats
# from .nr_frequency import NRFrequency

SAMPLERS = [
    # Kubectl
    KubectlTop,
    # # K8
    # K8BasicStats,
    # # NR
    NRTop,
    # NRBasicStats,
    # NRFrequency,
    # Dummy samplers for testing purposes
    _DummySampler,
    _DummyFileCount
]