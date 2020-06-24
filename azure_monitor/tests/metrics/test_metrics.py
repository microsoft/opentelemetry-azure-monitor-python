# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import os
import shutil
import unittest
from unittest import mock

from opentelemetry import metrics
from opentelemetry.sdk.metrics import (
    Counter,
    MeterProvider,
    ValueObserver,
    ValueRecorder,
)
from opentelemetry.sdk.metrics.export import MetricRecord, MetricsExportResult
from opentelemetry.sdk.metrics.export.aggregate import (
    MinMaxSumCountAggregator,
    SumAggregator,
    ValueObserverAggregator,
)
from opentelemetry.sdk.util import ns_to_iso_str

from azure_monitor.export import ExportResult
from azure_monitor.export.metrics import AzureMonitorMetricsExporter
from azure_monitor.options import ExporterOptions
from azure_monitor.protocol import Data, DataPoint, Envelope, MetricData

TEST_FOLDER = os.path.abspath(".test")
STORAGE_PATH = os.path.join(TEST_FOLDER)


# pylint: disable=invalid-name
def setUpModule():
    os.makedirs(TEST_FOLDER)


# pylint: disable=invalid-name
def tearDownModule():
    shutil.rmtree(TEST_FOLDER)


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
        cls._exporter = AzureMonitorMetricsExporter(storage_path=STORAGE_PATH)

        metrics.set_meter_provider(MeterProvider())
        cls._meter = metrics.get_meter(__name__)
        cls._test_metric = cls._meter.create_metric(
            "testname", "testdesc", "unit", int, Counter, ["environment"]
        )
        cls._test_value_recorder = cls._meter.create_metric(
            "testname", "testdesc", "unit", int, ValueRecorder, ["environment"]
        )
        cls._test_obs = cls._meter.register_observer(
            lambda x: x,
            "testname",
            "testdesc",
            "unit",
            int,
            ValueObserver,
            ["environment"],
        )
        cls._test_labels = tuple({"environment": "staging"}.items())

    def setUp(self):
        for filename in os.listdir(STORAGE_PATH):
            file_path = os.path.join(STORAGE_PATH, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except OSError as e:
                print("Failed to delete %s. Reason: %s" % (file_path, e))

    @classmethod
    def tearDownClass(cls):
        metrics._METER_PROVIDER = None

    def test_constructor(self):
        """Test the constructor."""
        exporter = AzureMonitorMetricsExporter(
            instrumentation_key="4321abcd-5678-4efa-8abc-1234567890ab",
            storage_path=os.path.join(TEST_FOLDER, self.id()),
        )
        self.assertIsInstance(exporter.options, ExporterOptions)
        self.assertEqual(
            exporter.options.instrumentation_key,
            "4321abcd-5678-4efa-8abc-1234567890ab",
        )

    @mock.patch(
        "azure_monitor.export.metrics.AzureMonitorMetricsExporter._transmit"
    )
    @mock.patch(
        "azure_monitor.export.metrics.AzureMonitorMetricsExporter._metric_to_envelope"
    )
    def test_export(self, mte, transmit):
        record = MetricRecord(
            SumAggregator(), self._test_labels, self._test_metric
        )
        exporter = self._exporter
        mte.return_value = Envelope()
        transmit.return_value = ExportResult.SUCCESS
        result = exporter.export([record])
        self.assertEqual(result, MetricsExportResult.SUCCESS)

    @mock.patch(
        "azure_monitor.export.metrics.AzureMonitorMetricsExporter._transmit"
    )
    @mock.patch(
        "azure_monitor.export.metrics.AzureMonitorMetricsExporter._metric_to_envelope"
    )
    def test_export_failed_retryable(self, mte, transmit):
        record = MetricRecord(
            SumAggregator(), self._test_labels, self._test_metric
        )
        exporter = self._exporter
        transmit.return_value = ExportResult.FAILED_RETRYABLE
        mte.return_value = Envelope()
        storage_mock = mock.Mock()
        exporter.storage.put = storage_mock
        result = exporter.export([record])
        self.assertEqual(result, MetricsExportResult.FAILURE)
        self.assertEqual(storage_mock.call_count, 1)

    @mock.patch("azure_monitor.export.metrics.logger")
    @mock.patch(
        "azure_monitor.export.metrics.AzureMonitorMetricsExporter._transmit"
    )
    @mock.patch(
        "azure_monitor.export.metrics.AzureMonitorMetricsExporter._metric_to_envelope"
    )
    def test_export_exception(self, mte, transmit, logger_mock):
        record = MetricRecord(
            SumAggregator(), self._test_labels, self._test_metric
        )
        exporter = self._exporter
        mte.return_value = Envelope()
        transmit.side_effect = throw(Exception)
        result = exporter.export([record])
        self.assertEqual(result, MetricsExportResult.FAILURE)
        self.assertEqual(logger_mock.exception.called, True)

    def test_metric_to_envelope_none(self):
        exporter = self._exporter
        self.assertIsNone(exporter._metric_to_envelope(None))

    def test_metric_to_envelope(self):
        aggregator = SumAggregator()
        aggregator.update(123)
        aggregator.take_checkpoint()
        record = MetricRecord(self._test_metric, self._test_labels, aggregator)
        exporter = self._exporter
        envelope = exporter._metric_to_envelope(record)
        self.assertIsInstance(envelope, Envelope)
        self.assertEqual(envelope.ver, 1)
        self.assertEqual(envelope.name, "Microsoft.ApplicationInsights.Metric")
        self.assertEqual(
            envelope.time, ns_to_iso_str(aggregator.last_update_timestamp)
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
        aggregator = ValueObserverAggregator()
        aggregator.update(123)
        aggregator.take_checkpoint()
        record = MetricRecord(self._test_obs, self._test_labels, aggregator)
        print(record.labels)
        exporter = self._exporter
        envelope = exporter._metric_to_envelope(record)
        self.assertIsInstance(envelope, Envelope)
        self.assertEqual(envelope.ver, 1)
        self.assertEqual(envelope.name, "Microsoft.ApplicationInsights.Metric")
        self.assertEqual(
            envelope.time, ns_to_iso_str(aggregator.last_update_timestamp)
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

    def test_observer_to_envelope_value_none(self):
        aggregator = ValueObserverAggregator()
        aggregator.update(None)
        aggregator.take_checkpoint()
        record = MetricRecord(self._test_obs, self._test_labels, aggregator)
        exporter = self._exporter
        envelope = exporter._metric_to_envelope(record)
        self.assertIsInstance(envelope, Envelope)
        self.assertEqual(envelope.ver, 1)
        self.assertEqual(envelope.name, "Microsoft.ApplicationInsights.Metric")
        self.assertEqual(
            envelope.time, ns_to_iso_str(aggregator.last_update_timestamp)
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
        print(envelope.data.base_data.properties)
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

    def test_value_recorder_to_envelope(self):
        aggregator = MinMaxSumCountAggregator()
        aggregator.update(123)
        aggregator.take_checkpoint()
        record = MetricRecord(
            self._test_value_recorder, self._test_labels, aggregator
        )
        exporter = self._exporter
        envelope = exporter._metric_to_envelope(record)
        self.assertIsInstance(envelope, Envelope)
        self.assertEqual(envelope.ver, 1)
        self.assertEqual(envelope.name, "Microsoft.ApplicationInsights.Metric")
        self.assertEqual(
            envelope.time, ns_to_iso_str(aggregator.last_update_timestamp)
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
        self.assertEqual(envelope.data.base_data.metrics[0].value, 1)
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
