# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import unittest
from unittest import mock

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider, Observer

from azure_monitor.sdk.auto_collection import dependency_metrics
from azure_monitor.sdk.auto_collection.metrics_span_processor import (
    AzureMetricsSpanProcessor,
)


# pylint: disable=protected-access
class TestDependencyMetrics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        metrics.set_meter_provider(MeterProvider())
        cls._meter = metrics.get_meter(__name__)
        cls._test_labels = {"environment": "staging"}
        cls._span_processor = AzureMetricsSpanProcessor()

    @classmethod
    def tearDown(cls):
        metrics._METER_PROVIDER = None

    def setUp(self):
        dependency_metrics.dependency_map.clear()

    def test_constructor(self):
        mock_meter = mock.Mock()
        metrics_collector = dependency_metrics.DependencyMetrics(
            meter=mock_meter,
            labels=self._test_labels,
            span_processor=self._span_processor,
        )
        self.assertEqual(metrics_collector._meter, mock_meter)
        self.assertEqual(metrics_collector._labels, self._test_labels)
        self.assertEqual(mock_meter.register_observer.call_count, 3)

        create_metric_calls = mock_meter.register_observer.call_args_list
        create_metric_calls[0].assert_called_with(
            callback=metrics_collector._track_dependency_duration,
            name="\\ApplicationInsights\\Dependency Call Duration",
            description="Average Outgoing Requests duration",
            unit="milliseconds",
            value_type=int,
        )
        create_metric_calls[1].assert_called_with(
            callback=metrics_collector._track_failure_rate,
            name="\\ApplicationInsights\\Dependency Calls Failed/Sec",
            description="Failed Outgoing Requests per second",
            unit="rps",
            value_type=float,
        )
        create_metric_calls[2].assert_called_with(
            callback=metrics_collector._track_dependency_rate,
            name="\\ApplicationInsights\\Dependency Calls/Sec",
            description="Outgoing Requests per second",
            unit="rps",
            value_type=float,
        )

    @mock.patch("azure_monitor.sdk.auto_collection.dependency_metrics.time")
    def test_track_dependency_rate(self, time_mock):
        time_mock.time.return_value = 100
        metrics_collector = dependency_metrics.DependencyMetrics(
            meter=self._meter,
            labels=self._test_labels,
            span_processor=self._span_processor,
        )
        obs = Observer(
            callback=metrics_collector._track_dependency_rate,
            name="\\ApplicationInsights\\Dependency Calls/Sec",
            description="Outgoing Requests per second",
            unit="rps",
            value_type=float,
            meter=self._meter,
        )
        dependency_metrics.dependency_map["last_time"] = 98.0
        self._span_processor.dependency_count = 4
        metrics_collector._track_dependency_rate(obs)
        self.assertEqual(
            obs.aggregators[tuple(self._test_labels.items())].current, 2
        )

    @mock.patch("azure_monitor.sdk.auto_collection.dependency_metrics.time")
    def test_track_dependency_rate_time_none(self, time_mock):
        time_mock.time.return_value = 100
        metrics_collector = dependency_metrics.DependencyMetrics(
            meter=self._meter,
            labels=self._test_labels,
            span_processor=self._span_processor,
        )
        dependency_metrics.dependency_map["last_time"] = None
        obs = Observer(
            callback=metrics_collector._track_dependency_rate,
            name="\\ApplicationInsights\\Dependency Calls/Sec",
            description="Outgoing Requests per second",
            unit="rps",
            value_type=float,
            meter=self._meter,
        )
        metrics_collector._track_dependency_rate(obs)
        self.assertEqual(
            obs.aggregators[tuple(self._test_labels.items())].current, 0.0
        )

    @mock.patch("azure_monitor.sdk.auto_collection.dependency_metrics.time")
    def test_track_dependency_rate_error(self, time_mock):
        time_mock.time.return_value = 100
        metrics_collector = dependency_metrics.DependencyMetrics(
            meter=self._meter,
            labels=self._test_labels,
            span_processor=self._span_processor,
        )
        dependency_metrics.dependency_map["last_time"] = 100
        dependency_metrics.dependency_map["last_result"] = 5.0
        obs = Observer(
            callback=metrics_collector._track_dependency_rate,
            name="\\ApplicationInsights\\Dependency Calls/Sec",
            description="Outgoing Requests per second",
            unit="rps",
            value_type=float,
            meter=self._meter,
        )
        metrics_collector._track_dependency_rate(obs)
        self.assertEqual(
            obs.aggregators[tuple(self._test_labels.items())].current, 5.0
        )

    @mock.patch("azure_monitor.sdk.auto_collection.dependency_metrics.time")
    def test_track_failed_dependency_rate(self, time_mock):
        time_mock.time.return_value = 100
        metrics_collector = dependency_metrics.DependencyMetrics(
            meter=self._meter,
            labels=self._test_labels,
            span_processor=self._span_processor,
        )
        obs = Observer(
            callback=metrics_collector._track_failure_rate,
            name="test",
            description="test",
            unit="test",
            value_type=float,
            meter=self._meter,
        )
        dependency_metrics.dependency_map["last_time"] = 98
        self._span_processor.failed_dependency_count = 4
        metrics_collector._track_failure_rate(obs)
        self.assertEqual(
            obs.aggregators[tuple(self._test_labels.items())].current, 2.0
        )

    @mock.patch("azure_monitor.sdk.auto_collection.dependency_metrics.time")
    def test_track_failed_dependency_rate_time_none(self, time_mock):
        time_mock.time.return_value = 100
        metrics_collector = dependency_metrics.DependencyMetrics(
            meter=self._meter,
            labels=self._test_labels,
            span_processor=self._span_processor,
        )
        dependency_metrics.dependency_map["last_time"] = None
        obs = Observer(
            callback=metrics_collector._track_failure_rate,
            name="test",
            description="test",
            unit="test",
            value_type=float,
            meter=self._meter,
        )
        metrics_collector._track_failure_rate(obs)
        self.assertEqual(
            obs.aggregators[tuple(self._test_labels.items())].current, 0.0
        )

    @mock.patch("azure_monitor.sdk.auto_collection.dependency_metrics.time")
    def test_track_failed_dependency_rate_error(self, time_mock):
        time_mock.time.return_value = 100
        metrics_collector = dependency_metrics.DependencyMetrics(
            meter=self._meter,
            labels=self._test_labels,
            span_processor=self._span_processor,
        )
        dependency_metrics.dependency_map["last_time"] = 100
        dependency_metrics.dependency_map["last_result"] = 5.0
        obs = Observer(
            callback=metrics_collector._track_failure_rate,
            name="test",
            description="test",
            unit="test",
            value_type=float,
            meter=self._meter,
        )
        metrics_collector._track_failure_rate(obs)
        self.assertEqual(
            obs.aggregators[tuple(self._test_labels.items())].current, 5.0
        )

    def test_track_dependency_duration(self):
        metrics_collector = dependency_metrics.DependencyMetrics(
            meter=self._meter,
            labels=self._test_labels,
            span_processor=self._span_processor,
        )
        self._span_processor.dependency_duration = 100
        self._span_processor.dependency_count = 10
        dependency_metrics.dependency_map["last_count"] = 5
        obs = Observer(
            callback=metrics_collector._track_dependency_duration,
            name="test",
            description="test",
            unit="test",
            value_type=int,
            meter=self._meter,
        )
        metrics_collector._track_dependency_duration(obs)
        self.assertEqual(
            obs.aggregators[tuple(self._test_labels.items())].current, 20
        )

    def test_track_dependency_duration_error(self):
        metrics_collector = dependency_metrics.DependencyMetrics(
            meter=self._meter,
            labels=self._test_labels,
            span_processor=self._span_processor,
        )
        self._span_processor.dependency_duration = 100
        self._span_processor.dependency_count = 10
        dependency_metrics.dependency_map["last_count"] = 10
        obs = Observer(
            callback=metrics_collector._track_dependency_duration,
            name="test",
            description="test",
            unit="test",
            value_type=int,
            meter=self._meter,
        )
        metrics_collector._track_dependency_duration(obs)
        self.assertEqual(
            obs.aggregators[tuple(self._test_labels.items())].current, 0
        )
