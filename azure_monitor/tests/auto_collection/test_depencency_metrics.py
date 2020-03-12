# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import unittest
from http.server import HTTPServer
from unittest import mock

import requests
from opentelemetry import metrics
from opentelemetry.sdk.metrics import Gauge, Meter

from azure_monitor.auto_collection import DependencyMetrics, dependency_metrics

ORIGINAL_FUNCTION = requests.Session.request
ORIGINAL_CONS = HTTPServer.__init__


# pylint: disable=protected-access
class TestDependencyMetrics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._meter_defaults = (metrics._METER, metrics._METER_FACTORY)
        metrics.set_preferred_meter_implementation(lambda _: Meter())
        cls._meter = metrics.meter()
        kvp = {"environment": "staging"}
        cls._test_label_set = cls._meter.get_label_set(kvp)

    @classmethod
    def tearDown(cls):
        metrics._METER, metrics._METER_FACTORY = cls._meter_defaults

    def setUp(self):
        dependency_metrics.dependency_map.clear()
        requests.Session.request = ORIGINAL_FUNCTION
        dependency_metrics.ORIGINAL_CONSTRUCTOR = ORIGINAL_CONS

    def test_constructor(self):
        mock_meter = mock.Mock()
        metrics_collector = DependencyMetrics(
            meter=mock_meter, label_set=self._test_label_set
        )
        self.assertEqual(metrics_collector._meter, mock_meter)
        self.assertEqual(metrics_collector._label_set, self._test_label_set)

        self.assertEqual(mock_meter.create_metric.call_count, 1)

        create_metric_calls = mock_meter.create_metric.call_args_list

        self.assertEqual(
            create_metric_calls[0][0],
            (
                "\\ApplicationInsights\\Dependency Calls/Sec",
                "Outgoing Requests per second",
                "rps",
                int,
                Gauge,
            ),
        )

    @mock.patch("azure_monitor.auto_collection.dependency_metrics.time")
    def test_track_depencency_rate(self, time_mock):
        time_mock.time.return_value = 100
        metrics_collector = DependencyMetrics(
            meter=self._meter, label_set=self._test_label_set
        )
        dependency_metrics.dependency_map["last_time"] = 98
        dependency_metrics.dependency_map["count"] = 4
        metrics_collector._track_dependency_rate()
        self.assertEqual(
            metrics_collector._dependency_rate_handle.aggregator.current, 2
        )

    @mock.patch("azure_monitor.auto_collection.dependency_metrics.time")
    def test_track_depencency_rate_error(self, time_mock):
        time_mock.time.return_value = 100
        metrics_collector = DependencyMetrics(
            meter=self._meter, label_set=self._test_label_set
        )
        dependency_metrics.dependency_map["last_time"] = 100
        dependency_metrics.dependency_map["last_result"] = 5
        metrics_collector._track_dependency_rate()
        self.assertEqual(
            metrics_collector._dependency_rate_handle.aggregator.current, 5
        )

    def test_dependency_patch(self):
        dependency_metrics.ORIGINAL_REQUEST = lambda x: None
        session = requests.Session()
        result = dependency_metrics.dependency_patch(session)

        self.assertEqual(dependency_metrics.dependency_map["count"], 1)
        self.assertIsNone(result)
