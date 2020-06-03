# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
#
from typing import Dict

from opentelemetry.metrics import Meter

from azure_monitor.sdk.auto_collection.dependency_metrics import (
    DependencyMetrics,
)
from azure_monitor.sdk.auto_collection.metrics_span_processor import (
    AzureMetricsSpanProcessor,
)
from azure_monitor.sdk.auto_collection.performance_metrics import (
    PerformanceMetrics,
)
from azure_monitor.sdk.auto_collection.request_metrics import RequestMetrics

__all__ = [
    "AutoCollection",
    "AzureMetricsSpanProcessor",
    "DependencyMetrics",
    "RequestMetrics",
    "PerformanceMetrics",
]


class AutoCollection:
    """Starts auto collection of standard metrics, including performance,
    dependency and request metrics.

    Args:
        meter: OpenTelemetry Meter
        labels: Dictionary of labels
    """

    def __init__(
        self,
        meter: Meter,
        labels: Dict[str, str],
        span_processor: AzureMetricsSpanProcessor,
    ):
        self._performance_metrics = PerformanceMetrics(meter, labels)
        self._dependency_metrics = DependencyMetrics(
            meter, labels, span_processor
        )
        self._request_metrics = RequestMetrics(meter, labels, span_processor)
