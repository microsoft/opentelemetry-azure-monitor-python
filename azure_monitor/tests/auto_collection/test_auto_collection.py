# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import unittest
from unittest import mock

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider

from azure_monitor.auto_collection import AutoCollection


# pylint: disable=protected-access
class TestAutoCollection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        metrics.set_meter_provider(MeterProvider())
        cls._meter = metrics.get_meter(__name__)
        kvp = {"environment": "staging"}
        cls._test_label_set = cls._meter.get_label_set(kvp)

    @classmethod
    def tearDownClass(cls):
        metrics._METER_PROVIDER = None

    @mock.patch(
        "azure_monitor.auto_collection.PerformanceMetrics", autospec=True
    )
    @mock.patch(
        "azure_monitor.auto_collection.DependencyMetrics", autospec=True
    )
    @mock.patch("azure_monitor.auto_collection.RequestMetrics", autospec=True)
    def test_constructor(
        self, mock_performance, mock_dependencies, mock_requests
    ):
        """Test the constructor."""
        AutoCollection(meter=self._meter, label_set=self._test_label_set)
        self.assertEqual(mock_performance.called, True)
        self.assertEqual(mock_dependencies.called, True)
        self.assertEqual(mock_requests.called, True)
        self.assertEqual(mock_performance.call_args[0][0], self._meter)
        self.assertEqual(
            mock_performance.call_args[0][1], self._test_label_set
        )
        self.assertEqual(mock_dependencies.call_args[0][0], self._meter)
        self.assertEqual(
            mock_dependencies.call_args[0][1], self._test_label_set
        )
        self.assertEqual(mock_requests.call_args[0][0], self._meter)
        self.assertEqual(mock_requests.call_args[0][1], self._test_label_set)
