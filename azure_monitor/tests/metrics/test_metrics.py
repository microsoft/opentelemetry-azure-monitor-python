# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import json
import os
import shutil
import unittest
from unittest import mock

from opentelemetry import metrics
from opentelemetry.sdk.metrics import Counter, Meter
from opentelemetry.sdk.metrics.export import MetricRecord, MetricsExportResult
from opentelemetry.sdk.metrics.export.aggregate import CounterAggregator
from opentelemetry.sdk.util import ns_to_iso_str

from azure_monitor.export import ExportResult
from azure_monitor.export.metrics import AzureMonitorMetricsExporter
from azure_monitor.options import ExporterOptions
from azure_monitor.protocol import Data, Envelope, MetricData


class TestAzureMetricsExporter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ[
            "APPINSIGHTS_INSTRUMENTATIONKEY"
        ] = "1234abcd-5678-4efa-8abc-1234567890ab"

        cls._meter_defaults = (metrics._METER, metrics._METER_FACTORY)
        metrics.set_preferred_meter_implementation(lambda _: Meter())
        cls._meter = metrics.meter()
        cls._test_metric = cls._meter.create_metric(
            "testname", "testdesc", "unit", int, Counter, ["environment"]
        )
        kvp = {"environment": "staging"}
        cls._test_label_set = cls._meter.get_label_set(kvp)

    @classmethod
    def tearDownClass(cls):
        metrics._METER, metrics._METER_PROVIDER_FACTORY = cls._meter_defaults

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

    def test_metric_to_envelope(self):
        aggregator = CounterAggregator()
        aggregator.update(123)
        aggregator.take_checkpoint()
        record = MetricRecord(
            aggregator, self._test_label_set, self._test_metric
        )
        exporter = AzureMonitorMetricsExporter()
        envelope = exporter.metric_to_envelope(record)
        self.assertIsInstance(envelope, Envelope)
        self.assertEqual(envelope.ver, 1)
        self.assertEqual(envelope.name, "Microsoft.ApplicationInsights.Metric")
        self.assertEqual(
            envelope.time,
            ns_to_iso_str(
                record.metric.get_handle(
                    record.label_set
                ).last_update_timestamp
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


class MockResponse(object):
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text


class MockTransport(object):
    def __init__(self, exporter=None):
        self.export_called = False
        self.exporter = exporter

    def export(self, datas):
        self.export_called = True
