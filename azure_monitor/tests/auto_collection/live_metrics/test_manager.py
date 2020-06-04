# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import time
import unittest
from unittest import mock

from opentelemetry import metrics
from opentelemetry.sdk.metrics import Counter, MeterProvider

from azure_monitor.sdk.auto_collection.live_metrics.exporter import (
    LiveMetricsExporter,
)
from azure_monitor.sdk.auto_collection.live_metrics.manager import (
    LiveMetricsManager,
    LiveMetricsPing,
    LiveMetricsPost,
)
from azure_monitor.sdk.auto_collection.metrics_span_processor import (
    AzureMetricsSpanProcessor,
)


# pylint: disable=protected-access
class TestLiveMetricsManager(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        metrics.set_meter_provider(MeterProvider())
        cls._meter = metrics.get_meter(__name__)
        cls._test_metric = cls._meter.create_metric(
            "testname", "testdesc", "unit", int, Counter, ["environment"]
        )
        testing_labels = {"environment": "testing"}
        cls._test_metric.add(5, testing_labels)
        cls._instrumentation_key = "99c42f65-1656-4c41-afde-bd86b709a4a7"
        cls._manager = None
        cls._ping = None
        cls._post = None
        cls._span_processor = AzureMetricsSpanProcessor()

    @classmethod
    def tearDownClass(cls):
        metrics._METER_PROVIDER = None

    def tearDown(self):
        if self._manager:
            self._manager.shutdown()
            self._manager = None
        if self._ping:
            self._ping.shutdown()
            self._ping = None
        if self._post:
            self._post.shutdown()
            self._post = None

    def test_constructor(self):
        """Test the constructor."""
        with mock.patch("requests.post"):
            self._manager = LiveMetricsManager(
                meter=self._meter,
                instrumentation_key=self._instrumentation_key,
                span_processor=self._span_processor,
            )
            self.assertFalse(self._manager._is_user_subscribed)
            self.assertEqual(
                self._manager._instrumentation_key, self._instrumentation_key
            )
            self.assertEqual(self._manager._meter, self._meter)
            self.assertIsNotNone(self._manager._ping)

    def test_switch(self):
        """Test manager switch between ping and post."""
        with mock.patch("requests.post") as request:
            request.return_value = MockResponse(
                200, None, {"x-ms-qps-subscribed": "true"}
            )
            self._manager = LiveMetricsManager(
                meter=self._meter,
                instrumentation_key=self._instrumentation_key,
                span_processor=self._span_processor,
            )
            self._manager.interval = 60
            time.sleep(1)
            self._manager.check_if_user_is_subscribed()
            self.assertIsNone(self._manager._ping)
            self.assertIsNotNone(self._manager._post)
            self._manager._post.is_user_subscribed = False
            self._manager.check_if_user_is_subscribed()
            self.assertIsNone(self._manager._post)
            self.assertIsNotNone(self._manager._ping)

    def test_ping_ok(self):
        """Test ping send requests to Live Metrics service."""
        with mock.patch("requests.post") as request:
            request.return_value = MockResponse(200, None, {})
            self._ping = LiveMetricsPing(
                instrumentation_key=self._instrumentation_key
            )
            self._ping.ping()
            self.assertTrue(request.called)
            self.assertTrue(self._ping.last_request_success_time > 0)
            self.assertTrue(self._ping.last_send_succeeded)
            self.assertFalse(self._ping.is_user_subscribed)

    def test_ping_subscribed(self):
        """Test ping when user is subscribed."""
        with mock.patch("requests.post") as request:
            request.return_value = MockResponse(
                200, None, {"x-ms-qps-subscribed": "true"}
            )
            self._ping = LiveMetricsPing(
                instrumentation_key=self._instrumentation_key
            )
            self._ping.ping()
            self.assertTrue(self._ping.is_user_subscribed)

    def test_ping_error(self):
        """Test ping when failure."""
        with mock.patch("requests.post") as request:
            request.return_value = MockResponse(400, None, {})
            self._ping = LiveMetricsPing(
                instrumentation_key=self._instrumentation_key
            )
            self._ping.last_request_success_time = time.time() - 60
            self._ping.ping()
            self.assertFalse(self._ping.last_send_succeeded)
            self.assertEqual(self._ping.interval, 60)

    def test_post_ok(self):
        """Test post send requests to Live Metrics service."""
        with mock.patch("requests.post") as request:
            request.return_value = MockResponse(
                200, None, {"x-ms-qps-subscribed": "false"}
            )
            self._post = LiveMetricsPost(
                exporter=LiveMetricsExporter(
                    self._instrumentation_key,
                    span_processor=self._span_processor,
                ),
                meter=self._meter,
                instrumentation_key=self._instrumentation_key,
            )
            self._post.post()
            self.assertTrue(request.called)
            self.assertTrue(self._post.last_request_success_time > 0)
            self.assertTrue(self._post.last_send_succeeded)
            self.assertFalse(self._post.is_user_subscribed)

    def test_post_subscribed(self):
        """Test post when user is subscribed."""
        with mock.patch("requests.post") as request:
            request.return_value = MockResponse(
                200, None, {"x-ms-qps-subscribed": "true"}
            )
            self._post = LiveMetricsPost(
                exporter=LiveMetricsExporter(
                    self._instrumentation_key,
                    span_processor=self._span_processor,
                ),
                meter=self._meter,
                instrumentation_key=self._instrumentation_key,
            )
            self._post.post()
            self.assertTrue(self._post.is_user_subscribed)

    def test_post_error(self):
        """Test post when failure."""
        with mock.patch("requests.post") as request:
            request.return_value = MockResponse(400, None, {})
            self._post = LiveMetricsPost(
                exporter=LiveMetricsExporter(
                    self._instrumentation_key,
                    span_processor=self._span_processor,
                ),
                meter=self._meter,
                instrumentation_key=self._instrumentation_key,
            )
            self._post.last_request_success_time = time.time() - 61
            self._post.post()
            self.assertFalse(self._post.last_send_succeeded)
            self.assertEqual(self._post.interval, 60)


# pylint: disable=invalid-name
class MockResponse:
    def __init__(self, status_code, text, headers):
        self.status_code = status_code
        self.text = text
        self.ok = status_code == 200
        self.headers = headers
