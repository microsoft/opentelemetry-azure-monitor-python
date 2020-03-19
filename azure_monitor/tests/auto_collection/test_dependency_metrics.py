# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import unittest
from http.server import HTTPServer
from unittest import mock

import requests
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider, Observer

from azure_monitor.auto_collection import DependencyMetrics, dependency_metrics

ORIGINAL_FUNCTION = requests.Session.request
ORIGINAL_CONS = HTTPServer.__init__


# pylint: disable=protected-access
class TestDependencyMetrics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        metrics.set_meter_provider(MeterProvider())
        cls._meter = metrics.get_meter(__name__)
        kvp = {"environment": "staging"}
        cls._test_label_set = cls._meter.get_label_set(kvp)

    @classmethod
    def tearDown(cls):
        metrics._METER_PROVIDER = None

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
        self.assertEqual(mock_meter.register_observer.call_count, 1)
        mock_meter.register_observer.assert_called_with(
            callback=metrics_collector._track_dependency_rate,
            name="\\ApplicationInsights\\Dependency Calls/Sec",
            description="Outgoing Requests per second",
            unit="rps",
            value_type=int,
        )

    @mock.patch("azure_monitor.auto_collection.dependency_metrics.time")
    def test_track_dependency_rate(self, time_mock):
        time_mock.time.return_value = 100
        metrics_collector = DependencyMetrics(
            meter=self._meter, label_set=self._test_label_set
        )
        obs = Observer(
            callback=metrics_collector._track_dependency_rate,
            name="\\ApplicationInsights\\Dependency Calls/Sec",
            description="Outgoing Requests per second",
            unit="rps",
            value_type=int,
            meter=self._meter
        )
        dependency_metrics.dependency_map["last_time"] = 98
        dependency_metrics.dependency_map["count"] = 4
        metrics_collector._track_dependency_rate(obs)
        self.assertEqual(
            obs.aggregators[self._test_label_set].current, 2
        )

    @mock.patch("azure_monitor.auto_collection.dependency_metrics.time")
    def test_track_dependency_rate_time_none(self, time_mock):
        time_mock.time.return_value = 100
        metrics_collector = DependencyMetrics(
            meter=self._meter, label_set=self._test_label_set
        )
        dependency_metrics.dependency_map["last_time"] = None
        obs = Observer(
            callback=metrics_collector._track_dependency_rate,
            name="\\ApplicationInsights\\Dependency Calls/Sec",
            description="Outgoing Requests per second",
            unit="rps",
            value_type=int,
            meter=self._meter
        )
        metrics_collector._track_dependency_rate(obs)
        self.assertEqual(
            obs.aggregators[self._test_label_set].current, 0
        )

    @mock.patch("azure_monitor.auto_collection.dependency_metrics.time")
    def test_track_dependency_rate_error(self, time_mock):
        time_mock.time.return_value = 100
        metrics_collector = DependencyMetrics(
            meter=self._meter, label_set=self._test_label_set
        )
        dependency_metrics.dependency_map["last_time"] = 100
        dependency_metrics.dependency_map["last_result"] = 5
        obs = Observer(
            callback=metrics_collector._track_dependency_rate,
            name="\\ApplicationInsights\\Dependency Calls/Sec",
            description="Outgoing Requests per second",
            unit="rps",
            value_type=int,
            meter=self._meter
        )
        metrics_collector._track_dependency_rate(obs)
        self.assertEqual(
            obs.aggregators[self._test_label_set].current, 5
        )

    def test_dependency_patch(self):
        dependency_metrics.ORIGINAL_REQUEST = lambda x: None
        session = requests.Session()
        result = dependency_metrics.dependency_patch(session)

        self.assertEqual(dependency_metrics.dependency_map["count"], 1)
        self.assertIsNone(result)
