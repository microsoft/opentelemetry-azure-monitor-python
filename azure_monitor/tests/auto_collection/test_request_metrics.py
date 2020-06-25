# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import unittest
from http.server import HTTPServer
from unittest import mock

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider, Observer

from azure_monitor.sdk.auto_collection import request_metrics
from azure_monitor.sdk.auto_collection.utils import AutoCollectionType

ORIGINAL_CONS = HTTPServer.__init__


# pylint: disable=protected-access
class TestRequestMetrics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        metrics.set_meter_provider(MeterProvider())
        cls._meter = metrics.get_meter(__name__)
        cls._test_labels = {"environment": "staging"}

    @classmethod
    def tearDown(cls):
        metrics._METER_PROVIDER = None

    def setUp(self):
        request_metrics.requests_map.clear()
        request_metrics.ORIGINAL_CONSTRUCTOR = ORIGINAL_CONS

    def test_constructor(self):
        mock_meter = mock.Mock()
        request_metrics_collector = request_metrics.RequestMetrics(
            meter=mock_meter,
            labels=self._test_labels,
            collection_type=AutoCollectionType.STANDARD_METRICS,
        )
        self.assertEqual(request_metrics_collector._meter, mock_meter)
        self.assertEqual(request_metrics_collector._labels, self._test_labels)
        self.assertEqual(mock_meter.register_observer.call_count, 2)
        create_metric_calls = mock_meter.register_observer.call_args_list
        create_metric_calls[0].assert_called_with(
            callback=request_metrics_collector._track_request_duration,
            name="\\ASP.NET Applications(??APP_W3SVC_PROC??)\\Request Execution Time",
            description="Incoming Requests Average Execution Time",
            unit="milliseconds",
            value_type=int,
        )

        create_metric_calls[1].assert_called_with(
            callback=request_metrics_collector._track_request_rate,
            name="\\ASP.NET Applications(??APP_W3SVC_PROC??)\\Requests/Sec",
            description="Incoming Requests Rate",
            unit="rps",
            value_type=float,
        )

    def test_track_request_duration(self):
        request_metrics_collector = request_metrics.RequestMetrics(
            meter=self._meter,
            labels=self._test_labels,
            collection_type=AutoCollectionType.STANDARD_METRICS,
        )
        request_metrics.requests_map["duration"] = 100
        request_metrics.requests_map["count"] = 10
        request_metrics.requests_map["last_count"] = 5
        obs = Observer(
            callback=request_metrics_collector._track_request_duration,
            name="\\ASP.NET Applications(??APP_W3SVC_PROC??)\\Request Execution Time",
            description="Incoming Requests Average Execution Time",
            unit="milliseconds",
            value_type=int,
            meter=self._meter,
        )
        request_metrics_collector._track_request_duration(obs)
        self.assertEqual(
            obs.aggregators[tuple(self._test_labels.items())].current, 20.0
        )

    def test_track_request_duration_error(self):
        request_metrics_collector = request_metrics.RequestMetrics(
            meter=self._meter,
            labels=self._test_labels,
            collection_type=AutoCollectionType.STANDARD_METRICS,
        )
        request_metrics.requests_map["duration"] = 100
        request_metrics.requests_map["count"] = 10
        request_metrics.requests_map["last_count"] = 10
        obs = Observer(
            callback=request_metrics_collector._track_request_duration,
            name="\\ASP.NET Applications(??APP_W3SVC_PROC??)\\Request Execution Time",
            description="Incoming Requests Average Execution Time",
            unit="milliseconds",
            value_type=int,
            meter=self._meter,
        )
        request_metrics_collector._track_request_duration(obs)
        self.assertEqual(
            obs.aggregators[tuple(self._test_labels.items())].current, 0.0
        )

    @mock.patch("azure_monitor.sdk.auto_collection.request_metrics.time")
    def test_track_request_rate(self, time_mock):
        request_metrics_collector = request_metrics.RequestMetrics(
            meter=self._meter,
            labels=self._test_labels,
            collection_type=AutoCollectionType.STANDARD_METRICS,
        )
        time_mock.time.return_value = 100
        request_metrics.requests_map["last_time"] = 98
        request_metrics.requests_map["count"] = 4
        obs = Observer(
            callback=request_metrics_collector._track_request_rate,
            name="\\ASP.NET Applications(??APP_W3SVC_PROC??)\\Requests/Sec",
            description="Incoming Requests Average Execution Rate",
            unit="rps",
            value_type=float,
            meter=self._meter,
        )
        request_metrics_collector._track_request_rate(obs)
        self.assertEqual(
            obs.aggregators[tuple(self._test_labels.items())].current, 2.0
        )

    @mock.patch("azure_monitor.sdk.auto_collection.request_metrics.time")
    def test_track_request_rate_time_none(self, time_mock):
        time_mock.time.return_value = 100
        request_metrics_collector = request_metrics.RequestMetrics(
            meter=self._meter,
            labels=self._test_labels,
            collection_type=AutoCollectionType.STANDARD_METRICS,
        )
        request_metrics.requests_map["last_time"] = None
        obs = Observer(
            callback=request_metrics_collector._track_request_rate,
            name="\\ASP.NET Applications(??APP_W3SVC_PROC??)\\Requests/Sec",
            description="Incoming Requests Average Execution Rate",
            unit="rps",
            value_type=float,
            meter=self._meter,
        )
        request_metrics_collector._track_request_rate(obs)
        self.assertEqual(
            obs.aggregators[tuple(self._test_labels.items())].current, 0.0
        )

    @mock.patch("azure_monitor.sdk.auto_collection.request_metrics.time")
    def test_track_request_rate_error(self, time_mock):
        request_metrics_collector = request_metrics.RequestMetrics(
            meter=self._meter,
            labels=self._test_labels,
            collection_type=AutoCollectionType.STANDARD_METRICS,
        )
        time_mock.time.return_value = 100
        request_metrics.requests_map["last_rate"] = 5.0
        request_metrics.requests_map["last_time"] = 100
        obs = Observer(
            callback=request_metrics_collector._track_request_rate,
            name="\\ASP.NET Applications(??APP_W3SVC_PROC??)\\Requests/Sec",
            description="Incoming Requests Average Execution Rate",
            unit="rps",
            value_type=float,
            meter=self._meter,
        )
        request_metrics_collector._track_request_rate(obs)
        self.assertEqual(
            obs.aggregators[tuple(self._test_labels.items())].current, 5.0
        )

    def test_request_patch(self):
        map = request_metrics.requests_map  # pylint: disable=redefined-builtin
        func = mock.Mock()
        new_func = request_metrics.request_patch(func)
        new_func()

        self.assertEqual(map["count"], 1)
        self.assertIsNotNone(map["duration"])
        self.assertEqual(len(func.call_args_list), 1)

    def test_server_patch(self):
        request_metrics.ORIGINAL_CONSTRUCTOR = lambda x, y, z: None
        with mock.patch(
            "azure_monitor.sdk.auto_collection.request_metrics.request_patch"
        ) as request_mock:
            handler = mock.Mock()
            handler.do_DELETE.return_value = None
            handler.do_GET.return_value = None
            handler.do_HEAD.return_value = None
            handler.do_OPTIONS.return_value = None
            handler.do_POST.return_value = None
            handler.do_PUT.return_value = None
            result = request_metrics.server_patch(None, None, handler)
            handler.do_DELETE()
            handler.do_GET()
            handler.do_HEAD()
            handler.do_OPTIONS()
            handler.do_POST()
            handler.do_PUT()

            self.assertEqual(result, None)
            self.assertEqual(len(request_mock.call_args_list), 6)

    def test_server_patch_no_methods(self):
        request_metrics.ORIGINAL_CONSTRUCTOR = lambda x, y, z: None
        with mock.patch(
            "azure_monitor.sdk.auto_collection.request_metrics.request_patch"
        ) as request_mock:
            handler = mock.Mock()
            result = request_metrics.server_patch(None, None, handler)
            handler.do_DELETE()
            handler.do_GET()
            handler.do_HEAD()
            handler.do_OPTIONS()
            handler.do_POST()
            handler.do_PUT()

            self.assertEqual(result, None)
            self.assertEqual(len(request_mock.call_args_list), 0)

    def test_server_patch_no_args(self):
        request_metrics.ORIGINAL_CONSTRUCTOR = lambda x, y: None
        req = request_metrics.server_patch(None, None)

        self.assertEqual(req, None)

    def test_server_patch_no_handler(self):
        request_metrics.ORIGINAL_CONSTRUCTOR = lambda x, y, z: None
        req = request_metrics.server_patch(None, None, None)
        self.assertEqual(req, None)
