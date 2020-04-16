# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
#
import threading
import time

from opentelemetry.sdk.metrics.export import MetricsExportResult

from azure_monitor.sdk.auto_collection import live_metrics
from azure_monitor.sdk.auto_collection.live_metrics.exporter import (
    LiveMetricsExporter,
)
from azure_monitor.sdk.auto_collection.live_metrics.sender import (
    LiveMetricsSender,
)

FALLBACK_INTERVAL = 60
PING_INTERVAL = 5
POST_INTERVAL = 1
MAIN_INTERVAL = 2


class LiveMetricsManager(threading.Thread):

    daemon = True

    def __init__(self, meter, instrumentation_key):
        super().__init__()
        self.thread_event = threading.Event()
        self.interval = MAIN_INTERVAL
        self._instrumentation_key = instrumentation_key
        self._is_user_subscribed = False
        self._meter = meter
        self._post = None
        self._ping = LiveMetricsPing(self._instrumentation_key)
        self.start()

    def run(self):
        self.check_if_user_is_subscribed()
        while not self.thread_event.wait(self.interval):
            self.check_if_user_is_subscribed()

    def check_if_user_is_subscribed(self):
        if self._ping:
            if self._ping.is_user_subscribed:
                # Switch to Post
                self._ping.shutdown()
                self._ping = None
                self._post = LiveMetricsPost(
                    self._meter, self._instrumentation_key
                )
        if self._post:
            if not self._post.is_user_subscribed:
                # Switch to Ping
                self._post.shutdown()
                self._post = None
                self._ping = LiveMetricsPing(self._instrumentation_key)

    def shutdown(self):
        if self._ping:
            self._ping.shutdown()
        if self._post:
            self._post.shutdown()
        self.thread_event.set()


class LiveMetricsPing(threading.Thread):

    daemon = True

    def __init__(self, instrumentation_key):
        super().__init__()
        self.instrumentation_key = instrumentation_key
        self.thread_event = threading.Event()
        self.interval = PING_INTERVAL
        self.is_user_subscribed = False
        self.last_send_succeeded = False
        self.last_request_success_time = 0
        self.sender = LiveMetricsSender(self.instrumentation_key)
        self.start()

    def run(self):
        self.ping()
        while not self.thread_event.wait(self.interval):
            self.ping()

    def ping(self):
        envelope = live_metrics.create_metric_envelope(
            self.instrumentation_key
        )
        response = self.sender.ping(envelope)
        if response.ok:
            if not self.last_send_succeeded:
                self.interval = PING_INTERVAL
                self.last_send_succeeded = True
            self.last_request_success_time = time.time()
            if (
                response.headers.get(
                    live_metrics.LIVE_METRICS_SUBSCRIBED_HEADER
                )
                == "true"
            ):
                self.is_user_subscribed = True
        else:
            self.last_send_succeeded = False
            if time.time() >= self.last_request_success_time + 20:
                self.interval = FALLBACK_INTERVAL

    def shutdown(self):
        self.thread_event.set()


class LiveMetricsPost(threading.Thread):

    daemon = True

    def __init__(self, meter, instrumentation_key):
        super().__init__()
        self.instrumentation_key = instrumentation_key
        self.meter = meter
        self.thread_event = threading.Event()
        self.interval = POST_INTERVAL
        self.is_user_subscribed = True
        self.last_send_succeeded = False
        self.last_request_success_time = time.time()
        self.exporter = LiveMetricsExporter(self.instrumentation_key)
        self.start()

    def run(self):
        self.post()
        while not self.thread_event.wait(self.interval):
            self.post()

    def post(self):
        self.meter.collect()
        result = self.exporter.export(self.meter.batcher.checkpoint_set())
        self.meter.batcher.finished_collection()
        if result == MetricsExportResult.SUCCESS:
            self.last_request_success_time = time.time()
            if not self.last_send_succeeded:
                self.interval = POST_INTERVAL
                self.last_send_succeeded = True

            if self.exporter.subscribed:
                self.is_user_subscribed = True
        else:
            self.last_send_succeeded = False
            if time.time() >= self.last_request_success_time + 60:
                self.interval = FALLBACK_INTERVAL

    def shutdown(self):
        self.thread_event.set()
