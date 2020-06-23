# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
#
from typing import Dict

from opentelemetry.metrics import Meter

from azure_monitor.sdk.auto_collection import AutoCollectionType
from azure_monitor.sdk.auto_collection.dependency_metrics import (
    DependencyMetrics,
)
from azure_monitor.sdk.auto_collection.live_metrics.manager import (
    LiveMetricsManager,
)
from azure_monitor.sdk.auto_collection.metrics_span_processor import (
    AzureMetricsSpanProcessor,
)
from azure_monitor.sdk.auto_collection.performance_metrics import (
    PerformanceMetrics,
)
from azure_monitor.sdk.auto_collection.request_metrics import RequestMetrics

__all__ = ["LiveMetricsAutoCollection"]


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
        instrumentation_key: str,
    ):
        col_type = AutoCollectionType.LIVE_METRICS
        self._performance_metrics = PerformanceMetrics(meter, labels, col_type)
        self._dependency_metrics = DependencyMetrics(
            meter, labels, span_processor
        )
        self._request_metrics = RequestMetrics(
            meter, labels, span_processor, col_type
        )
        self._manager = LiveMetricsManager(
            meter, instrumentation_key, span_processor
        )

    def shutdown(self):
        self._manager.shutdown()
