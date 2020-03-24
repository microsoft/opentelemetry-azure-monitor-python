# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import os
import unittest
from unittest import mock

from opentelemetry import metrics
from opentelemetry.sdk.metrics import Counter, Measure, MeterProvider
from opentelemetry.sdk.metrics.export import MetricRecord, MetricsExportResult
from opentelemetry.sdk.metrics.export.aggregate import (
    CounterAggregator,
    MinMaxSumCountAggregator,
    ObserverAggregator,
)
from opentelemetry.sdk.util import ns_to_iso_str

from azure_monitor.export import ExportResult
from azure_monitor.export.metrics import AzureMonitorMetricsExporter
from azure_monitor.options import ExporterOptions
from azure_monitor.protocol import Data, DataPoint, Envelope, MetricData


def throw(exc_type, *args, **kwargs):
    def func(*_args, **_kwargs):
        raise exc_type(*args, **kwargs)

    return func


# pylint: disable=protected-access
class TestAzureMetricsExporter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ[
            "APPINSIGHTS_INSTRUMENTATIONKEY"
        ] = "1234abcd-5678-4efa-8abc-1234567890ab"

        metrics.set_meter_provider(MeterProvider())
        cls._meter = metrics.get_meter(__name__)
        cls._test_metric = cls._meter.create_metric(
            "testname", "testdesc", "unit", int, Counter, ["environment"]
        )
        cls._test_measure = cls._meter.create_metric(
            "testname", "testdesc", "unit", int, Measure, ["environment"]
        )
        cls._test_obs = cls._meter.register_observer(
            lambda x: x,
            "testname",
            "testdesc",
            "unit",
            int,
            Counter,
            ["environment"],
        )
        kvp = {"environment": "staging"}
        cls._test_label_set = cls._meter.get_label_set(kvp)

    @classmethod
    def tearDownClass(cls):
        metrics._METER_PROVIDER = None

    def test_constructor(self):
        """Test the constructor."""
        exporter = AzureMonitorMetricsExporter(
            instrumentation_key="4321abcd-5678-4efa-8abc-1234567890ab"
        )
        self.assertIsInstance(exporter.options, ExporterOptions)
        self.assertEqual(
            exporter.options.instrumentation_key,
            "4321abcd-5678-4efa-8abc-1234567890ab",
        )

    def test_export(self,):
        record = MetricRecord(
            CounterAggregator(), self._test_label_set, self._test_metric
        )
        exporter = AzureMonitorMetricsExporter()
        with mock.patch(
            "azure_monitor.export.metrics.AzureMonitorMetricsExporter._transmit"
        ) as transmit:  # noqa: E501
            transmit.return_value = ExportResult.SUCCESS
            result = exporter.export([record])
            self.assertEqual(result, MetricsExportResult.SUCCESS)

    def test_export_failed_retryable(self):
        record = MetricRecord(
            CounterAggregator(), self._test_label_set, self._test_metric
        )
        exporter = AzureMonitorMetricsExporter()
        with mock.patch(
            "azure_monitor.export.metrics.AzureMonitorMetricsExporter._transmit"
        ) as transmit:  # noqa: E501
            transmit.return_value = ExportResult.FAILED_RETRYABLE
            storage_mock = mock.Mock()
            exporter.storage.put = storage_mock
            result = exporter.export([record])
            self.assertEqual(result, MetricsExportResult.FAILED_RETRYABLE)
            self.assertEqual(storage_mock.call_count, 1)

    @mock.patch("azure_monitor.export.metrics.logger")
    def test_export_exception(self, logger_mock):
        record = MetricRecord(
            CounterAggregator(), self._test_label_set, self._test_metric
        )
        exporter = AzureMonitorMetricsExporter()
        with mock.patch(
            "azure_monitor.export.metrics.AzureMonitorMetricsExporter._transmit",
            throw(Exception),
        ):  # noqa: E501
            result = exporter.export([record])
            self.assertEqual(result, MetricsExportResult.FAILED_NOT_RETRYABLE)
            self.assertEqual(logger_mock.exception.called, True)

    def test_metric_to_envelope_none(self):
        exporter = AzureMonitorMetricsExporter()
        self.assertIsNone(exporter._metric_to_envelope(None))

    def test_metric_to_envelope(self):
        aggregator = CounterAggregator()
        aggregator.update(123)
        aggregator.take_checkpoint()
        record = MetricRecord(
            aggregator, self._test_label_set, self._test_metric
        )
        exporter = AzureMonitorMetricsExporter()
        envelope = exporter._metric_to_envelope(record)
        self.assertIsInstance(envelope, Envelope)
        self.assertEqual(envelope.ver, 1)
        self.assertEqual(envelope.name, "Microsoft.ApplicationInsights.Metric")
        self.assertEqual(
            envelope.time,
            ns_to_iso_str(
                record.metric.bind(record.label_set).last_update_timestamp
            ),
        )
        self.assertEqual(envelope.sample_rate, None)
        self.assertEqual(envelope.seq, None)
        self.assertEqual(envelope.ikey, "1234abcd-5678-4efa-8abc-1234567890ab")
        self.assertEqual(envelope.flags, None)

        self.assertIsInstance(envelope.data, Data)
        self.assertIsInstance(envelope.data.base_data, MetricData)
        self.assertEqual(envelope.data.base_data.ver, 2)
        self.assertEqual(len(envelope.data.base_data.metrics), 1)
        self.assertIsInstance(envelope.data.base_data.metrics[0], DataPoint)
        self.assertEqual(envelope.data.base_data.metrics[0].ns, "testdesc")
        self.assertEqual(envelope.data.base_data.metrics[0].name, "testname")
        self.assertEqual(envelope.data.base_data.metrics[0].value, 123)
        self.assertEqual(
            envelope.data.base_data.properties["environment"], "staging"
        )
        self.assertIsNotNone(envelope.tags["ai.cloud.role"])
        self.assertIsNotNone(envelope.tags["ai.cloud.roleInstance"])
        self.assertIsNotNone(envelope.tags["ai.device.id"])
        self.assertIsNotNone(envelope.tags["ai.device.locale"])
        self.assertIsNotNone(envelope.tags["ai.device.osVersion"])
        self.assertIsNotNone(envelope.tags["ai.device.type"])
        self.assertIsNotNone(envelope.tags["ai.internal.sdkVersion"])

    def test_observer_to_envelope(self):
        aggregator = ObserverAggregator()
        aggregator.update(123)
        aggregator.take_checkpoint()
        record = MetricRecord(aggregator, self._test_label_set, self._test_obs)
        exporter = AzureMonitorMetricsExporter()
        envelope = exporter._metric_to_envelope(record)
        self.assertIsInstance(envelope, Envelope)
        self.assertEqual(envelope.ver, 1)
        self.assertEqual(envelope.name, "Microsoft.ApplicationInsights.Metric")
        # TODO: implement last updated timestamp for observer
        # self.assertEqual(
        #     envelope.time,
        #     ns_to_iso_str(
        #         record.metric.bind(
        #             record.label_set
        #         ).last_update_timestamp
        #     ),
        # )
        self.assertEqual(envelope.sample_rate, None)
        self.assertEqual(envelope.seq, None)
        self.assertEqual(envelope.ikey, "1234abcd-5678-4efa-8abc-1234567890ab")
        self.assertEqual(envelope.flags, None)

        self.assertIsInstance(envelope.data, Data)
        self.assertIsInstance(envelope.data.base_data, MetricData)
        self.assertEqual(envelope.data.base_data.ver, 2)
        self.assertEqual(len(envelope.data.base_data.metrics), 1)
        self.assertIsInstance(envelope.data.base_data.metrics[0], DataPoint)
        self.assertEqual(envelope.data.base_data.metrics[0].ns, "testdesc")
        self.assertEqual(envelope.data.base_data.metrics[0].name, "testname")
        self.assertEqual(envelope.data.base_data.metrics[0].value, 123)
        self.assertEqual(
            envelope.data.base_data.properties["environment"], "staging"
        )
        self.assertIsNotNone(envelope.tags["ai.cloud.role"])
        self.assertIsNotNone(envelope.tags["ai.cloud.roleInstance"])
        self.assertIsNotNone(envelope.tags["ai.device.id"])
        self.assertIsNotNone(envelope.tags["ai.device.locale"])
        self.assertIsNotNone(envelope.tags["ai.device.osVersion"])
        self.assertIsNotNone(envelope.tags["ai.device.type"])
        self.assertIsNotNone(envelope.tags["ai.internal.sdkVersion"])

    @mock.patch("azure_monitor.export.metrics.logger")
    def test_measure_to_envelope(self, logger_mock):
        aggregator = MinMaxSumCountAggregator()
        aggregator.update(123)
        aggregator.take_checkpoint()
        record = MetricRecord(
            aggregator, self._test_label_set, self._test_measure
        )
        exporter = AzureMonitorMetricsExporter()
        envelope = exporter._metric_to_envelope(record)
        self.assertIsInstance(envelope, Envelope)
        self.assertEqual(envelope.ver, 1)
        self.assertEqual(envelope.name, "Microsoft.ApplicationInsights.Metric")
        self.assertEqual(
            envelope.time,
            ns_to_iso_str(
                record.metric.bind(record.label_set).last_update_timestamp
            ),
        )
        self.assertEqual(envelope.sample_rate, None)
        self.assertEqual(envelope.seq, None)
        self.assertEqual(envelope.ikey, "1234abcd-5678-4efa-8abc-1234567890ab")
        self.assertEqual(envelope.flags, None)

        self.assertIsInstance(envelope.data, Data)
        self.assertIsInstance(envelope.data.base_data, MetricData)
        self.assertEqual(envelope.data.base_data.ver, 2)
        self.assertEqual(len(envelope.data.base_data.metrics), 1)
        self.assertIsInstance(envelope.data.base_data.metrics[0], DataPoint)
        self.assertEqual(envelope.data.base_data.metrics[0].ns, "testdesc")
        self.assertEqual(envelope.data.base_data.metrics[0].name, "testname")
        self.assertEqual(envelope.data.base_data.metrics[0].value, 0)
        self.assertEqual(
            envelope.data.base_data.properties["environment"], "staging"
        )
        self.assertIsNotNone(envelope.tags["ai.cloud.role"])
        self.assertIsNotNone(envelope.tags["ai.cloud.roleInstance"])
        self.assertIsNotNone(envelope.tags["ai.device.id"])
        self.assertIsNotNone(envelope.tags["ai.device.locale"])
        self.assertIsNotNone(envelope.tags["ai.device.osVersion"])
        self.assertIsNotNone(envelope.tags["ai.device.type"])
        self.assertIsNotNone(envelope.tags["ai.internal.sdkVersion"])
        self.assertEqual(logger_mock.warning.called, True)
