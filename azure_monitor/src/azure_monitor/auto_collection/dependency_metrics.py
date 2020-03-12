# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import threading
import time

import requests
from opentelemetry.metrics import LabelSet, Meter
from opentelemetry.sdk.metrics import Gauge

dependency_map = dict()
_dependency_lock = threading.Lock()
ORIGINAL_REQUEST = requests.Session.request


def dependency_patch(*args, **kwargs) -> None:
    result = ORIGINAL_REQUEST(*args, **kwargs)
    # We don't want multiple threads updating this at once
    with _dependency_lock:
        count = dependency_map.get("count", 0)
        dependency_map["count"] = count + 1
    return result


class DependencyMetrics:
    def __init__(self, meter: Meter, label_set: LabelSet):
        self._meter = meter
        self._label_set = label_set
        # Patch requests
        requests.Session.request = dependency_patch
        dependency_rate_metric = self._meter.create_metric(
            "\\ApplicationInsights\\Dependency Calls/Sec",
            "Outgoing Requests per second",
            "rps",
            int,
            Gauge,
        )
        self._dependency_rate_handle = dependency_rate_metric.get_handle(
            self._label_set
        )

    def track(self) -> None:
        self._track_dependency_rate()

    def _track_dependency_rate(self) -> None:
        """ Track Dependency rate

        Calculated by obtaining the number of outgoing requests made
        using the requests library within an elapsed time and dividing that
        value over the elapsed time.
        """
        current_count = dependency_map.get("count", 0)
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
            self._dependency_rate_handle.set(int(result))
        except ZeroDivisionError:
            # If elapsed_seconds is 0, exporter call made too close to previous
            # Return the previous result if this is the case
            self._dependency_rate_handle.set(int(last_result))
