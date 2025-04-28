from typing import Callable, Dict, Iterable

import pandas as pd
from prometheus_client.metrics_core import Metric


def metrics_to_pd_series(families: Iterable[Metric], custom_maps: Dict[str, Callable] = None):
    # https://prometheus.io/docs/concepts/data_model/
    series = pd.Series()

    for family in families:
        if custom_maps is not None and family.name in custom_maps:
            for name, value in custom_maps[family.name](family):
                series[name] = value
        else:
            for sample in family.samples:
                name = family.name
                for label, value in sample.labels.items():
                    name += f"-{label}={value}"
                series[name] = sample.value

    return series

def mapper_python_info(metric: Metric) -> dict:
    assert metric.name == "python_info" and len(metric.samples) == 1

    sample = metric.samples[0]
    return (
        ("python_implementation", sample.labels["implementation"]),
        ("python_version", sample.labels["version"])
    )