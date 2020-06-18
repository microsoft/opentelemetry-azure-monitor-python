# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import unittest
from unittest import mock

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider

from azure_monitor.sdk.auto_collection import (
    AutoCollection,
    AzureMetricsSpanProcessor,
)


# pylint: disable=protected-access
class TestAutoCollection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        metrics.set_meter_provider(MeterProvider())
        cls._meter = metrics.get_meter(__name__)
        cls._test_labels = tuple({"environment": "staging"}.items())
        cls._span_processor = AzureMetricsSpanProcessor()

    @classmethod
    def tearDownClass(cls):
        metrics._METER_PROVIDER = None

    @mock.patch(
        "azure_monitor.sdk.auto_collection.PerformanceMetrics", autospec=True
    )
    @mock.patch(
        "azure_monitor.sdk.auto_collection.RequestMetrics", autospec=True
    )
    def test_constructor(self, mock_requests, mock_performance):
        """Test the constructor."""

        AutoCollection(
            meter=self._meter,
            labels=self._test_labels,
            span_processor=self._span_processor,
        )
        self.assertEqual(mock_performance.called, True)
        self.assertEqual(mock_requests.called, True)
        self.assertEqual(mock_performance.call_args[0][0], self._meter)
        self.assertEqual(mock_performance.call_args[0][1], self._test_labels)
        self.assertEqual(mock_requests.call_args[0][0], self._meter)
        self.assertEqual(mock_requests.call_args[0][1], self._test_labels)
