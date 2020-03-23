# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
#
from opentelemetry.metrics import LabelSet, Meter

from azure_monitor.auto_collection.dependency_metrics import DependencyMetrics
from azure_monitor.auto_collection.performance_metrics import (
    PerformanceMetrics,
)
from azure_monitor.auto_collection.request_metrics import RequestMetrics

__all__ = [
    "AutoCollection",
    "DependencyMetrics",
    "RequestMetrics",
    "PerformanceMetrics",
]


class AutoCollection:
    """Starts auto collection of standard metrics, including performance, dependency and request metrics.

    Args:
        meter: OpenTelemetry Meter
        label_set: OpenTelemetry label set
    """

    def __init__(self, meter: Meter, label_set: LabelSet):
        self._performance_metrics = PerformanceMetrics(meter, label_set)
        self._dependency_metrics = DependencyMetrics(meter, label_set)
        self._request_metrics = RequestMetrics(meter, label_set)
