# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import time
from typing import Dict

from opentelemetry.metrics import Meter, Observer

from azure_monitor.sdk.auto_collection.metrics_span_processor import (
    AzureMetricsSpanProcessor,
)
from azure_monitor.sdk.auto_collection.utils import AutoCollectionType

dependency_map = dict()


class DependencyMetrics:
    """Auto collection of dependency metrics, including
    "Outgoing Requests per second", "Outgoing Request rate" and "Failed Outgoing Request rate" metrics.

    Args:
        meter: OpenTelemetry Meter
        labels: Dictionary of labels
        span_processor: Azure Metrics Span Processor
        collection_type: Standard or Live Metrics
    """

    def __init__(
        self,
        meter: Meter,
        labels: Dict[str, str],
        span_processor: AzureMetricsSpanProcessor,
        collection_type: AutoCollectionType,
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
            name="\\ApplicationInsights\\Dependency Calls Failed/Sec",
            description="Failed Outgoing Requests per second",
            unit="rps",
            value_type=int,
        )
        if collection_type == AutoCollectionType.STANDARD_METRICS:
            meter.register_observer(
                callback=self._track_dependency_rate,
                name="\\ApplicationInsights\\Dependency Calls/Sec",
                description="Outgoing Requests per second",
                unit="rps",
                value_type=int,
            )

    def _track_dependency_rate(self, observer: Observer) -> None:
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

    def _track_dependency_duration(self, observer: Observer) -> None:
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

    def _track_failure_rate(self, observer: Observer) -> None:
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
