# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import threading
import time

import requests
from opentelemetry import context
from opentelemetry.metrics import Meter
from opentelemetry.sdk.metrics import LabelSet

dependency_map = dict()
_dependency_lock = threading.Lock()
ORIGINAL_REQUEST = requests.Session.request


def dependency_patch(*args, **kwargs) -> None:
    result = ORIGINAL_REQUEST(*args, **kwargs)
    # Only collect request metric if sent from non-exporter thread
    if context.get_value("suppress_instrumentation") is None:
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
            observer.observe(int(result), self._label_set)
        except ZeroDivisionError:
            # If elapsed_seconds is 0, exporter call made too close to previous
            # Return the previous result if this is the case
            observer.observe(int(last_result), self._label_set)
