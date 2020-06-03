# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import logging
import threading
import time
from http.server import HTTPServer
from typing import Dict

from opentelemetry.metrics import Meter

from azure_monitor.sdk.auto_collection.metrics_span_processor import (
    AzureMetricsSpanProcessor,
)

logger = logging.getLogger(__name__)

_requests_lock = threading.Lock()
requests_map = dict()
ORIGINAL_CONSTRUCTOR = HTTPServer.__init__


def request_patch(func):
    def wrapper(self=None):
        start_time = time.time()
        func(self)
        end_time = time.time()

        with _requests_lock:
            # Update Count
            count = requests_map.get("count", 0)
            requests_map["count"] = count + 1
            # Update duration
            duration = requests_map.get("duration", 0)
            requests_map["duration"] = duration + (end_time - start_time)

    return wrapper


class RequestMetrics:
    """Starts auto collection of request metrics, including
    "Incoming Requests Average Execution Time" and
    "Incoming Requests Average Execution Rate" metrics.

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
            callback=self._track_request_duration,
            name="\\ASP.NET Applications(??APP_W3SVC_PROC??)\\Request Execution Time",
            description="Incoming Requests Average Execution Time",
            unit="milliseconds",
            value_type=int,
        )

        meter.register_observer(
            callback=self._track_request_rate,
            name="\\ASP.NET Applications(??APP_W3SVC_PROC??)\\Requests/Sec",
            description="Incoming Requests Average Execution Rate",
            unit="rps",
            value_type=int,
        )

    def _track_request_duration(self, observer) -> None:
        """ Track Request execution time

        Calculated by getting the time it takes to make an incoming request
        and dividing over the amount of incoming requests over an elapsed time.
        """
        last_average_duration = requests_map.get("last_average_duration", 0)
        interval_duration = (
            self._span_processor.request_duration
            - requests_map.get("last_duration", 0)
        )
        interval_count = self._span_processor.request_count - requests_map.get(
            "last_count", 0
        )
        try:
            result = interval_duration / interval_count
            requests_map["last_count"] = self._span_processor.request_count
            requests_map["last_average_duration"] = result
            requests_map[
                "last_duration"
            ] = self._span_processor.request_duration
            # Convert to milliseconds
            observer.observe(int(result * 1000.0), self._labels)
        except ZeroDivisionError:
            # If interval_count is 0, exporter call made too close to previous
            # Return the previous result if this is the case
            observer.observe(int(last_average_duration * 1000.0), self._labels)

    def _track_request_rate(self, observer) -> None:
        """ Track Request execution rate

        Calculated by obtaining by getting the number of incoming requests
        made to an HTTPServer within an elapsed time and dividing that value
        over the elapsed time.
        """
        current_time = time.time()
        last_rate = requests_map.get("last_rate", 0)
        last_time = requests_map.get("last_time")

        try:
            # last_rate_time is None the first time this function is called
            if last_time is not None:
                interval_time = current_time - requests_map.get("last_time", 0)
                interval_count = (
                    self._span_processor.request_count
                    - requests_map.get("last_count", 0)
                )
                result = interval_count / interval_time
            else:
                result = 0
            requests_map["last_time"] = current_time
            requests_map["last_count"] = self._span_processor.request_count
            requests_map["last_rate"] = result
            observer.observe(int(result), self._labels)
        except ZeroDivisionError:
            # If elapsed_seconds is 0, exporter call made too close to previous
            # Return the previous result if this is the case
            observer.observe(int(last_rate), self._labels)
