# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import time
from typing import Dict

from opentelemetry.metrics import Meter

from azure_monitor.sdk.auto_collection.metrics_span_processor import (
    AzureMetricsSpanProcessor,
)

dependency_map = dict()


class DependencyLiveMetrics:
    """Starts auto collection of dependency live metrics.

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
            callback=self._track_dependency_duration,
            name="\\ApplicationInsights\\Dependency Call Duration",
            description="Average Outgoing Requests duration",
            unit="milliseconds",
            value_type=float,
        )
        meter.register_observer(
            callback=self._track_failure_rate,
            name="\\ApplicationInsights\\Dependency Calls Failed\/Sec",
            description="Failed Outgoing Requests per second",
            unit="rps",
            value_type=int,
        )

    def _track_dependency_duration(self, observer) -> None:
        """ Track Dependency average duration

        Calculated by getting the time it takes to make an outgoing request
        and dividing over the amount of outgoing requests over an elapsed time.
        """
        last_average_duration = dependency_map.get("last_average_duration", 0)
        interval_duration = (
            self._span_processor.dependency_duration
            - dependency_map.get("last_duration", 0)
        )
        interval_count = (
            self._span_processor.dependency_count
            - dependency_map.get("last_count", 0)
        )
        try:
            result = interval_duration / interval_count
            dependency_map[
                "last_count"
            ] = self._span_processor.dependency_count
            dependency_map["last_average_duration"] = result
            dependency_map[
                "last_duration"
            ] = self._span_processor.dependency_duration
            # Convert to milliseconds
            observer.observe(int(result * 1000.0), self._labels)
        except ZeroDivisionError:
            # If interval_count is 0, exporter call made too close to previous
            # Return the previous result if this is the case
            observer.observe(int(last_average_duration * 1000.0), self._labels)

    def _track_failure_rate(self, observer) -> None:
        """ Track Failed Dependency rate

        Calculated by obtaining the number of failed outgoing requests made
        using the requests library within an elapsed time and dividing
        that value over the elapsed time.
        """
        current_failed_count = self._span_processor.failed_dependency_count
        current_time = time.time()
        last_failed_count = dependency_map.get("last_failed_count", 0)
        last_time = dependency_map.get("last_time")
        last_result = dependency_map.get("last_result", 0)

        try:
            # last_time is None the very first time this function is called
            if last_time is not None:
                elapsed_seconds = current_time - last_time
                interval_failed_count = (
                    current_failed_count - last_failed_count
                )
                result = interval_failed_count / elapsed_seconds
            else:
                result = 0
            dependency_map["last_time"] = current_time
            dependency_map["last_failed_count"] = current_failed_count
            dependency_map["last_result"] = result
            observer.observe(int(result), self._labels)
        except ZeroDivisionError:
            # If elapsed_seconds is 0, exporter call made too close to previous
            # Return the previous result if this is the case
            observer.observe(int(last_result), self._labels)
