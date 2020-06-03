# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import logging
import time
from typing import Dict

from opentelemetry.metrics import Meter

from azure_monitor.sdk.auto_collection.metrics_span_processor import (
    AzureMetricsSpanProcessor,
)

logger = logging.getLogger(__name__)

requests_map = dict()


class RequestLiveMetrics:
    """Starts auto collection of request live metrics, including
    "Failed Incoming Requests Rate" metric.

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
            callback=self._track_request_failed_rate,
            name="\\ApplicationInsights\\Requests Failed/Sec",
            description="Incoming Requests Failed Rate",
            unit="rps",
            value_type=int,
        )

    def _track_request_failed_rate(self, observer) -> None:
        """ Track Request failed execution rate

        Calculated by obtaining by getting the number of failed incoming requests
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
                    self._span_processor.failed_request_count
                    - requests_map.get("last_failed_count", 0)
                )
                result = interval_count / interval_time
            else:
                result = 0
            requests_map["last_time"] = current_time
            requests_map[
                "last_failed_count"
            ] = self._span_processor.failed_request_count
            requests_map["last_rate"] = result
            observer.observe(int(result), self._labels)
        except ZeroDivisionError:
            # If elapsed_seconds is 0, exporter call made too close to previous
            # Return the previous result if this is the case
            observer.observe(int(last_rate), self._labels)
