# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import unittest
from unittest import mock

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider, Observer

from azure_monitor.sdk.auto_collection.live_metrics import request_metrics
from azure_monitor.sdk.auto_collection.metrics_span_processor import (
    AzureMetricsSpanProcessor,
)


# pylint: disable=protected-access
class TestRequestMetrics(unittest.TestCase):
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
        request_metrics.requests_map.clear()

    def test_constructor(self):
        mock_meter = mock.Mock()
        request_metrics_collector = request_metrics.RequestLiveMetrics(
            meter=mock_meter,
            labels=self._test_labels,
            span_processor=self._span_processor,
        )
        self.assertEqual(request_metrics_collector._meter, mock_meter)
        self.assertEqual(request_metrics_collector._labels, self._test_labels)
        self.assertEqual(mock_meter.register_observer.call_count, 1)

        create_metric_calls = mock_meter.register_observer.call_args_list

        create_metric_calls[0].assert_called_with(
            callback=request_metrics_collector._track_request_failed_rate,
            name="\ApplicationInsights\Requests Failed/Sec",
            description="Incoming Requests Failed Rate",
            unit="rps",
            value_type=int,
        )

    @mock.patch(
        "azure_monitor.sdk.auto_collection.live_metrics.request_metrics.time"
    )
    def test_track_request_rate(self, time_mock):
        request_metrics_collector = request_metrics.RequestLiveMetrics(
            meter=self._meter,
            labels=self._test_labels,
            span_processor=self._span_processor,
        )
        time_mock.time.return_value = 100
        request_metrics.requests_map["last_time"] = 98
        self._span_processor.failed_request_count = 4
        obs = Observer(
            callback=request_metrics_collector._track_request_failed_rate,
            name="test",
            description="test",
            unit="test",
            value_type=int,
            meter=self._meter,
        )
        request_metrics_collector._track_request_failed_rate(obs)
        self.assertEqual(
            obs.aggregators[tuple(self._test_labels.items())].current, 2
        )

    @mock.patch(
        "azure_monitor.sdk.auto_collection.live_metrics.request_metrics.time"
    )
    def test_track_request_rate_time_none(self, time_mock):
        time_mock.time.return_value = 100
        request_metrics_collector = request_metrics.RequestLiveMetrics(
            meter=self._meter,
            labels=self._test_labels,
            span_processor=self._span_processor,
        )
        request_metrics.requests_map["last_time"] = None
        obs = Observer(
            callback=request_metrics_collector._track_request_failed_rate,
            name="test",
            description="test",
            unit="test",
            value_type=int,
            meter=self._meter,
        )
        request_metrics_collector._track_request_failed_rate(obs)
        self.assertEqual(
            obs.aggregators[tuple(self._test_labels.items())].current, 0
        )

    @mock.patch(
        "azure_monitor.sdk.auto_collection.live_metrics.request_metrics.time"
    )
    def test_track_request_rate_error(self, time_mock):
        request_metrics_collector = request_metrics.RequestLiveMetrics(
            meter=self._meter,
            labels=self._test_labels,
            span_processor=self._span_processor,
        )
        time_mock.time.return_value = 100
        request_metrics.requests_map["last_rate"] = 5
        request_metrics.requests_map["last_time"] = 100
        obs = Observer(
            callback=request_metrics_collector._track_request_failed_rate,
            name="test",
            description="test",
            unit="test",
            value_type=int,
            meter=self._meter,
        )
        request_metrics_collector._track_request_failed_rate(obs)
        self.assertEqual(
            obs.aggregators[tuple(self._test_labels.items())].current, 5
        )
