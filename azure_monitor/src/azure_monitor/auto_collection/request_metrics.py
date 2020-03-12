# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import logging
import threading
import time
from http.server import HTTPServer

from opentelemetry.metrics import LabelSet, Meter
from opentelemetry.sdk.metrics import Gauge

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


def server_patch(*args, **kwargs):
    if len(args) >= 3:
        handler = args[2]
        if handler:
            # Patch the handler methods if they exist
            if "do_DELETE" in dir(handler):
                handler.do_DELETE = request_patch(handler.do_DELETE)
            if "do_GET" in dir(handler):
                handler.do_GET = request_patch(handler.do_GET)
            if "do_HEAD" in dir(handler):
                handler.do_HEAD = request_patch(handler.do_HEAD)
            if "do_OPTIONS" in dir(handler):
                handler.do_OPTIONS = request_patch(handler.do_OPTIONS)
            if "do_POST" in dir(handler):
                handler.do_POST = request_patch(handler.do_POST)
            if "do_PUT" in dir(handler):
                handler.do_PUT = request_patch(handler.do_PUT)
    result = ORIGINAL_CONSTRUCTOR(*args, **kwargs)
    return result


class RequestMetrics:
    def __init__(self, meter: Meter, label_set: LabelSet):
        self._meter = meter
        self._label_set = label_set
        # Patch the HTTPServer handler to track request information
        HTTPServer.__init__ = server_patch

        request_duration_metric = self._meter.create_metric(
            "\\ASP.NET Applications(??APP_W3SVC_PROC??)\\Request Execution Time",
            "Incoming Requests Average Execution Time",
            "milliseconds",
            int,
            Gauge,
        )
        self._request_duration_handle = request_duration_metric.get_handle(
            self._label_set
        )

        request_rate_metric = self._meter.create_metric(
            "\\ASP.NET Applications(??APP_W3SVC_PROC??)\\Requests/Sec",
            "Incoming Requests Average Execution Rate",
            "rps",
            int,
            Gauge,
        )
        self._request_rate_handle = request_rate_metric.get_handle(
            self._label_set
        )

    def track(self) -> None:
        self._track_request_duration()
        self._track_request_rate()

    def _track_request_duration(self) -> None:
        """ Track Request execution time

        Calculated by getting the time it takes to make an incoming request
        and dividing over the amount of incoming requests over an elapsed time.
        """
        last_average_duration = requests_map.get("last_average_duration", 0)
        interval_duration = requests_map.get("duration", 0) - requests_map.get(
            "last_duration", 0
        )
        interval_count = requests_map.get("count", 0) - requests_map.get(
            "last_count", 0
        )
        try:
            result = interval_duration / interval_count
            requests_map["last_average_duration"] = result
            requests_map["last_duration"] = requests_map.get("duration", 0)
            # Convert to milliseconds
            self._request_duration_handle.set(int(result * 1000.0))
        except ZeroDivisionError:
            # If interval_count is 0, exporter call made too close to previous
            # Return the previous result if this is the case
            self._request_duration_handle.set(
                int(last_average_duration * 1000.0)
            )

    def _track_request_rate(self) -> None:
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
                interval_count = requests_map.get(
                    "count", 0
                ) - requests_map.get("last_count", 0)
                result = interval_count / interval_time
            else:
                result = 0
            requests_map["last_time"] = current_time
            requests_map["last_count"] = requests_map.get("count", 0)
            requests_map["last_rate"] = result
            self._request_rate_handle.set(int(result))
        except ZeroDivisionError:
            # If elapsed_seconds is 0, exporter call made too close to previous
            # Return the previous result if this is the case
            self._request_rate_handle.set(int(last_rate))
