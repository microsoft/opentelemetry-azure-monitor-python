# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import collections
import unittest
from unittest import mock

from opentelemetry import metrics
from opentelemetry.sdk.metrics import Gauge, Meter

from azure_monitor.auto_collection import PerformanceMetrics


def throw(exc_type, *args, **kwargs):
    def func(*_args, **_kwargs):
        raise exc_type(*args, **kwargs)

    return func


# pylint: disable=protected-access
class TestPerformanceMetrics(unittest.TestCase):
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

    def test_constructor(self):
        mock_meter = mock.Mock()
        performance_metrics_collector = PerformanceMetrics(
            meter=mock_meter, label_set=self._test_label_set
        )
        self.assertEqual(performance_metrics_collector._meter, mock_meter)
        self.assertEqual(
            performance_metrics_collector._label_set, self._test_label_set
        )

        self.assertEqual(mock_meter.create_metric.call_count, 4)

        create_metric_calls = mock_meter.create_metric.call_args_list

        self.assertEqual(
            create_metric_calls[0][0],
            (
                "\\Processor(_Total)\\% Processor Time",
                "Processor time as a percentage",
                "percentage",
                float,
                Gauge,
            ),
        )
        self.assertEqual(
            create_metric_calls[1][0],
            (
                "\\Memory\\Available Bytes",
                "Amount of available memory in bytes",
                "byte",
                int,
                Gauge,
            ),
        )
        self.assertEqual(
            create_metric_calls[2][0],
            (
                "\\Process(??APP_WIN32_PROC??)\\% Processor Time",
                "Process CPU usage as a percentage",
                "percentage",
                float,
                Gauge,
            ),
        )
        self.assertEqual(
            create_metric_calls[3][0],
            (
                "\\Process(??APP_WIN32_PROC??)\\Private Bytes",
                "Amount of memory process has used in bytes",
                "byte",
                int,
                Gauge,
            ),
        )

    def test_track(self):
        mock_meter = mock.Mock()
        performance_metrics_collector = PerformanceMetrics(
            meter=mock_meter, label_set=self._test_label_set
        )
        cpu_mock = mock.Mock()
        process_mock = mock.Mock()
        memory_mock = mock.Mock()
        proc_memory_mock = mock.Mock()
        performance_metrics_collector._track_cpu = cpu_mock
        performance_metrics_collector._track_process_cpu = process_mock
        performance_metrics_collector._track_memory = memory_mock
        performance_metrics_collector._track_process_memory = proc_memory_mock
        performance_metrics_collector.track()
        self.assertEqual(cpu_mock.call_count, 1)
        self.assertEqual(process_mock.call_count, 1)
        self.assertEqual(memory_mock.call_count, 1)
        self.assertEqual(proc_memory_mock.call_count, 1)

    def test_track_cpu(self):
        performance_metrics_collector = PerformanceMetrics(
            meter=self._meter, label_set=self._test_label_set
        )
        with mock.patch("psutil.cpu_times_percent") as processor_mock:
            cpu = collections.namedtuple("cpu", "idle")
            cpu_times = cpu(idle=94.5)
            processor_mock.return_value = cpu_times
            performance_metrics_collector._track_cpu()
            self.assertEqual(
                performance_metrics_collector._cpu_handle.aggregator.current,
                5.5,
            )

    @mock.patch("azure_monitor.auto_collection.performance_metrics.psutil")
    def test_track_process_cpu(self, psutil_mock):
        with mock.patch(
            "azure_monitor.auto_collection.performance_metrics.PROCESS"
        ) as process_mock:
            performance_metrics_collector = PerformanceMetrics(
                meter=self._meter, label_set=self._test_label_set
            )
            process_mock.cpu_percent.return_value = 44.4
            psutil_mock.cpu_count.return_value = 2
            performance_metrics_collector._track_process_cpu()
            self.assertEqual(
                performance_metrics_collector._process_cpu_handle.aggregator.current,
                22.2,
            )

    @mock.patch("azure_monitor.auto_collection.performance_metrics.logger")
    def test_track_process_cpu_exception(self, logger_mock):
        with mock.patch(
            "azure_monitor.auto_collection.performance_metrics.psutil"
        ) as psutil_mock:
            performance_metrics_collector = PerformanceMetrics(
                meter=self._meter, label_set=self._test_label_set
            )
            psutil_mock.cpu_count.return_value = None
            performance_metrics_collector._track_process_cpu()
            self.assertEqual(logger_mock.exception.called, True)

    @mock.patch("psutil.virtual_memory")
    def test_track_memory(self, psutil_mock):
        performance_metrics_collector = PerformanceMetrics(
            meter=self._meter, label_set=self._test_label_set
        )
        memory = collections.namedtuple("memory", "available")
        vmem = memory(available=100)
        psutil_mock.return_value = vmem
        performance_metrics_collector._track_memory()
        self.assertEqual(
            performance_metrics_collector._memory_handle.aggregator.current,
            100,
        )

    def test_track_process_memory(self):
        with mock.patch(
            "azure_monitor.auto_collection.performance_metrics.PROCESS"
        ) as process_mock:
            performance_metrics_collector = PerformanceMetrics(
                meter=self._meter, label_set=self._test_label_set
            )
            memory = collections.namedtuple("memory", "rss")
            pmem = memory(rss=100)
            process_mock.memory_info.return_value = pmem
            performance_metrics_collector._track_process_memory()
            self.assertEqual(
                performance_metrics_collector._process_memory_handle.aggregator.current,
                100,
            )

    @mock.patch("azure_monitor.auto_collection.performance_metrics.logger")
    def test_track_process_memory_exception(self, logger_mock):
        with mock.patch(
            "azure_monitor.auto_collection.performance_metrics.PROCESS",
            throw(Exception),
        ):
            performance_metrics_collector = PerformanceMetrics(
                meter=self._meter, label_set=self._test_label_set
            )
            performance_metrics_collector._track_process_memory()
            self.assertEqual(logger_mock.exception.called, True)
