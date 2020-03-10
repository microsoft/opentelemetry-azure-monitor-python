# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
#
from opentelemetry.metrics import LabelSet, Meter

from azure_monitor.auto_collection.performance_metrics import (
    PerformanceMetrics,
)
from azure_monitor.auto_collection.http_dependency_metrics import (
    HttpDependencyMetrics,
)
from azure_monitor.auto_collection.http_request_metrics import (
    HttpRequestMetrics,
)
from azure_monitor.utils import PeriodicTask

__all__ = ["AutoCollection", "HttpDependencyMetrics", "HttpRequestMetrics", "PerformanceMetrics"]


class AutoCollection:
    def __init__(
        self, meter: Meter, label_set: LabelSet, collection_interval: int = 60
    ):
        self._performance_metrics = PerformanceMetrics(meter, label_set)
        self._dependency_metrics = HttpDependencyMetrics(meter, label_set)
        self._request_metrics = HttpRequestMetrics(meter, label_set)

        self._collect_task = PeriodicTask(
            interval=collection_interval, function=self.collect
        )

    def collect(self):
        self._performance_metrics.track()
        self._dependency_metrics.track()
        self._request_metrics.track()
