# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
#
from typing import Dict

from opentelemetry.metrics import Meter

from azure_monitor.sdk.auto_collection.live_metrics.dependency_metrics import (
    DependencyLiveMetrics,
)
from azure_monitor.sdk.auto_collection.live_metrics.exporter import (
    LiveMetricsExporter,
)
from azure_monitor.sdk.auto_collection.live_metrics.performance_metrics import (
    PerformanceLiveMetrics,
)
from azure_monitor.sdk.auto_collection.live_metrics.request_metrics import (
    RequestLiveMetrics,
)
from azure_monitor.sdk.auto_collection.metrics_span_processor import (
    AzureMetricsSpanProcessor,
)

__all__ = [
    "LiveMetricsAutoCollection",
    "LiveMetricsExporter",
    "DependencyLiveMetrics",
    "PerformanceLiveMetrics",
    "RequestLiveMetrics",
]


class LiveMetricsAutoCollection:
    """Starts auto collection of live metrics, including performance,
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
        self._performance_metrics = PerformanceLiveMetrics(meter, labels)
        self._dependency_metrics = DependencyLiveMetrics(
            meter, labels, span_processor
        )
        self._request_metrics = RequestLiveMetrics(
            meter, labels, span_processor
        )
