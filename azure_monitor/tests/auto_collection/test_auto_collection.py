# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.


import json
import os
import shutil
import unittest
from unittest import mock

from opentelemetry import metrics
from opentelemetry.sdk.metrics import Meter

from azure_monitor.auto_collection import AutoCollection
from azure_monitor.utils import PeriodicTask


class TestAutoCollection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._meter_defaults = (metrics._METER, metrics._METER_FACTORY)
        metrics.set_preferred_meter_implementation(lambda _: Meter())
        cls._meter = metrics.meter()
        kvp = {"environment": "staging"}
        cls._test_label_set = cls._meter.get_label_set(kvp)

    @classmethod
    def tearDownClass(cls):
        metrics._METER, metrics._METER_FACTORY = cls._meter_defaults

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

        auto_collector = AutoCollection(
            meter=self._meter,
            label_set=self._test_label_set,
            collection_interval=1000,
        )
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

        self.assertIsInstance(auto_collector._collect_task, PeriodicTask)
        self.assertEqual(auto_collector._collect_task.interval, 1000)

    @mock.patch(
        "azure_monitor.auto_collection.PerformanceMetrics.track", autospec=True
    )
    @mock.patch(
        "azure_monitor.auto_collection.DependencyMetrics.track", autospec=True
    )
    @mock.patch(
        "azure_monitor.auto_collection.RequestMetrics.track", autospec=True
    )
    def test_collect(self, mock_performance, mock_dependencies, mock_requests):
        """Test collect method."""

        auto_collector = AutoCollection(
            meter=self._meter, label_set=self._test_label_set
        )
        auto_collector.collect()
        self.assertEqual(mock_performance.called, True)
        self.assertEqual(mock_dependencies.called, True)
        self.assertEqual(mock_requests.called, True)
