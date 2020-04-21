# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import time
import unittest
from unittest import mock

from opentelemetry import metrics
from opentelemetry.sdk.metrics import Counter, Measure, MeterProvider

from azure_monitor.sdk.auto_collection.live_metrics.manager import (
    LiveMetricsManager,
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

    @classmethod
    def tearDownClass(cls):
        metrics._METER_PROVIDER = None

    def tearDown(self):
        self._manager.shutdown()

    def test_constructor(self):
        """Test the constructor."""
        with mock.patch("requests.post"):
            self._manager = LiveMetricsManager(
                meter=self._meter,
                instrumentation_key=self._instrumentation_key,
            )
            self.assertFalse(self._manager._is_user_subscribed)
            self.assertEqual(
                self._manager._instrumentation_key, self._instrumentation_key
            )
            self.assertEqual(self._manager._meter, self._meter)
            self.assertIsNotNone(self._manager._ping)

    def test_switch(self):
        """Test manager switch between ping and post."""
        with mock.patch("requests.post"):
            self._manager = LiveMetricsManager(
                meter=self._meter,
                instrumentation_key=self._instrumentation_key,
            )
            self._manager._ping.is_user_subscribed = True
            self._manager.check_if_user_is_subscribed()
            self.assertIsNone(self._manager._ping)
            self.assertIsNotNone(self._manager._post)
            self._manager._post.is_user_subscribed = False
            self._manager.check_if_user_is_subscribed()
            self.assertIsNone(self._manager._post)
            self.assertIsNotNone(self._manager._ping)

    def test_ping(self):
        """Test ping send requests to Live Metrics service."""
        with mock.patch("requests.post") as request:
            self._manager = LiveMetricsManager(
                meter=self._meter,
                instrumentation_key=self._instrumentation_key,
            )
            self._manager._ping.is_user_subscribed = True
            self._manager.check_if_user_is_subscribed()
            self.assertIsNone(self._manager._ping)
            self.assertIsNotNone(self._manager._post)
            self._manager._post.is_user_subscribed = False
            self._manager.check_if_user_is_subscribed()
            self.assertIsNone(self._manager._post)
            self.assertIsNotNone(self._manager._ping)
