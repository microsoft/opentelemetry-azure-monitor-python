# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import unittest
from http.server import HTTPServer
from unittest import mock

import requests
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider, Observer

from azure_monitor.sdk.auto_collection import dependency_metrics

ORIGINAL_FUNCTION = requests.Session.request
ORIGINAL_CONS = HTTPServer.__init__


# pylint: disable=protected-access
class TestDependencyMetrics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        metrics.set_meter_provider(MeterProvider())
        cls._meter = metrics.get_meter(__name__)
        cls._test_labels = {"environment": "staging"}

    @classmethod
    def tearDown(cls):
        metrics._METER_PROVIDER = None
        requests.Session.request = ORIGINAL_FUNCTION
        dependency_metrics.ORIGINAL_CONSTRUCTOR = ORIGINAL_CONS

    def setUp(self):
        dependency_metrics.dependency_map.clear()
        requests.Session.request = ORIGINAL_FUNCTION
        dependency_metrics.ORIGINAL_CONSTRUCTOR = ORIGINAL_CONS

    def test_constructor(self):
        mock_meter = mock.Mock()
        metrics_collector = dependency_metrics.DependencyMetrics(
            meter=mock_meter, labels=self._test_labels
        )
        self.assertEqual(metrics_collector._meter, mock_meter)
        self.assertEqual(metrics_collector._labels, self._test_labels)
        self.assertEqual(mock_meter.register_observer.call_count, 1)
        mock_meter.register_observer.assert_called_with(
            callback=metrics_collector._track_dependency_rate,
            name="\\ApplicationInsights\\Dependency Calls/Sec",
            description="Outgoing Requests per second",
            unit="rps",
            value_type=int,
        )

    @mock.patch("azure_monitor.sdk.auto_collection.dependency_metrics.time")
    def test_track_dependency_rate(self, time_mock):
        time_mock.time.return_value = 100
        metrics_collector = dependency_metrics.DependencyMetrics(
            meter=self._meter, labels=self._test_labels
        )
        obs = Observer(
            callback=metrics_collector._track_dependency_rate,
            name="\\ApplicationInsights\\Dependency Calls/Sec",
            description="Outgoing Requests per second",
            unit="rps",
            value_type=int,
            meter=self._meter,
        )
        dependency_metrics.dependency_map["last_time"] = 98
        dependency_metrics.dependency_map["count"] = 4
        metrics_collector._track_dependency_rate(obs)
        self.assertEqual(
            obs.aggregators[tuple(self._test_labels.items())].current, 2
        )

    @mock.patch("azure_monitor.sdk.auto_collection.dependency_metrics.time")
    def test_track_dependency_rate_time_none(self, time_mock):
        time_mock.time.return_value = 100
        metrics_collector = dependency_metrics.DependencyMetrics(
            meter=self._meter, labels=self._test_labels
        )
        dependency_metrics.dependency_map["last_time"] = None
        obs = Observer(
            callback=metrics_collector._track_dependency_rate,
            name="\\ApplicationInsights\\Dependency Calls/Sec",
            description="Outgoing Requests per second",
            unit="rps",
            value_type=int,
            meter=self._meter,
        )
        metrics_collector._track_dependency_rate(obs)
        self.assertEqual(
            obs.aggregators[tuple(self._test_labels.items())].current, 0
        )

    @mock.patch("azure_monitor.sdk.auto_collection.dependency_metrics.time")
    def test_track_dependency_rate_error(self, time_mock):
        time_mock.time.return_value = 100
        metrics_collector = dependency_metrics.DependencyMetrics(
            meter=self._meter, labels=self._test_labels
        )
        dependency_metrics.dependency_map["last_time"] = 100
        dependency_metrics.dependency_map["last_result"] = 5
        obs = Observer(
            callback=metrics_collector._track_dependency_rate,
            name="\\ApplicationInsights\\Dependency Calls/Sec",
            description="Outgoing Requests per second",
            unit="rps",
            value_type=int,
            meter=self._meter,
        )
        metrics_collector._track_dependency_rate(obs)
        self.assertEqual(
            obs.aggregators[tuple(self._test_labels.items())].current, 5
        )

    @mock.patch(
        "azure_monitor.sdk.auto_collection.dependency_metrics.ORIGINAL_REQUEST"
    )
    def test_dependency_patch(self, request_mock):
        session = requests.Session()
        dependency_metrics.dependency_patch(session)
        self.assertEqual(dependency_metrics.dependency_map["count"], 1)
        request_mock.assert_called_with(session)

    @mock.patch(
        "azure_monitor.sdk.auto_collection.dependency_metrics.ORIGINAL_REQUEST"
    )
    @mock.patch("azure_monitor.sdk.auto_collection.dependency_metrics.context")
    def test_dependency_patch_suppress(self, context_mock, request_mock):
        context_mock.get_value.return_value = {}
        session = requests.Session()
        dependency_metrics.dependency_patch(session)
        self.assertEqual(dependency_metrics.dependency_map.get("count"), None)
        request_mock.assert_called_with(session)
