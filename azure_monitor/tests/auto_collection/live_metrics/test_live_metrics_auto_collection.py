# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import unittest
from unittest import mock

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider

from azure_monitor.sdk.auto_collection import AzureMetricsSpanProcessor
from azure_monitor.sdk.auto_collection.live_metrics import (
    LiveMetricsAutoCollection,
)


# pylint: disable=protected-access
class TestLiveMetricsAutoCollection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        metrics.set_meter_provider(MeterProvider())
        cls._meter = metrics.get_meter(__name__)
        cls._test_labels = tuple({"environment": "staging"}.items())
        cls._span_processor = AzureMetricsSpanProcessor()

    @classmethod
    def tearDownClass(cls):
        metrics._METER_PROVIDER = None

    def setUp(self):
        self._auto_collection = LiveMetricsAutoCollection(
            meter=self._meter,
            labels=self._test_labels,
            span_processor=self._span_processor,
            instrumentation_key="TEST",
        )

    def tearDown(self):
        self._auto_collection.shutdown()

    def test_constructor(self):
        """Test the constructor."""
        self.assertIsNotNone(self._auto_collection._performance_metrics)
        self.assertIsNotNone(self._auto_collection._dependency_metrics)
        self.assertIsNotNone(self._auto_collection._request_metrics)
        self.assertIsNotNone(self._auto_collection._manager)
        # Check observers
        self.assertEqual(len(self._meter.observers), 4)
