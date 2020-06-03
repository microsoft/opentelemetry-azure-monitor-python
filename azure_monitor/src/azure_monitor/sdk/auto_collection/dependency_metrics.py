# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import time
from typing import Dict

from opentelemetry.metrics import Meter

from azure_monitor.sdk.auto_collection.metrics_span_processor import (
    AzureMetricsSpanProcessor,
)

dependency_map = dict()


class DependencyMetrics:
    """Starts auto collection of dependency metrics, including
    "Outgoing Requests per second" metric.

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
        self._meter = meter
        self._labels = labels
        self._span_processor = span_processor

        meter.register_observer(
            callback=self._track_dependency_rate,
            name="\\ApplicationInsights\\Dependency Calls/Sec",
            description="Outgoing Requests per second",
            unit="rps",
            value_type=int,
        )

    def _track_dependency_rate(self, observer) -> None:
        """ Track Dependency rate

        Calculated by obtaining the number of outgoing requests made
        using the requests library within an elapsed time and dividing
        that value over the elapsed time.
        """
        current_count = self._span_processor.dependency_count
        current_time = time.time()
        last_count = dependency_map.get("last_count", 0)
        last_time = dependency_map.get("last_time")
        last_result = dependency_map.get("last_result", 0)

        try:
            # last_time is None the very first time this function is called
            if last_time is not None:
                elapsed_seconds = current_time - last_time
                interval_count = current_count - last_count
                result = interval_count / elapsed_seconds
            else:
                result = 0
            dependency_map["last_time"] = current_time
            dependency_map["last_count"] = current_count
            dependency_map["last_result"] = result
            observer.observe(int(result), self._labels)
        except ZeroDivisionError:
            # If elapsed_seconds is 0, exporter call made too close to previous
            # Return the previous result if this is the case
            observer.observe(int(last_result), self._labels)
