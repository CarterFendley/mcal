from .dummy import _DummyFileCount, _DummySampler
from .k8_basic_stats import K8BasicStats
from .nr_basic_stats import NRBasicStats
from .nr_frequency import NRFrequency

SAMPLERS = [
    # K8
    K8BasicStats,
    # NR
    NRBasicStats,
    NRFrequency,
    # Dummy samplers for testing purposes
    _DummySampler,
    _DummyFileCount
]