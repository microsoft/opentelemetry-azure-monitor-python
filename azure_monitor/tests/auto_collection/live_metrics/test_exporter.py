# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import unittest
from unittest import mock

import requests
from opentelemetry import metrics
from opentelemetry.sdk.metrics import (
    Counter,
    MeterProvider,
    ValueObserver,
    ValueRecorder,
)
from opentelemetry.sdk.metrics.export import MetricRecord, MetricsExportResult
from opentelemetry.sdk.metrics.export.aggregate import (
    CounterAggregator,
    ValueObserverAggregator,
    MinMaxSumCountAggregator,
)

from azure_monitor.protocol import (
    Data,
    Envelope,
    LiveMetricEnvelope,
    RemoteDependency,
)
from azure_monitor.sdk.auto_collection.live_metrics.exporter import (
    LiveMetricsExporter,
)
from azure_monitor.sdk.auto_collection.metrics_span_processor import (
    AzureMetricsSpanProcessor,
)


def throw(exc_type, *args, **kwargs):
    def func(*_args, **_kwargs):
        raise exc_type(*args, **kwargs)

    return func


# pylint: disable=protected-access
class TestLiveMetricsExporter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._instrumentation_key = "99c42f65-1656-4c41-afde-bd86b709a4a7"
        metrics.set_meter_provider(MeterProvider())
        cls._meter = metrics.get_meter(__name__)
        cls._test_metric = cls._meter.create_metric(
            "testname", "testdesc", "unit", int, Counter, ["environment"]
        )
        cls._test_metric2 = cls._meter.create_metric(
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
        cls._span_processor = AzureMetricsSpanProcessor()

    def test_constructor(self):
        """Test the constructor."""
        exporter = LiveMetricsExporter(
            instrumentation_key=self._instrumentation_key,
            span_processor=self._span_processor,
        )
        self.assertEqual(exporter.subscribed, True)
        self.assertEqual(
            exporter._instrumentation_key, self._instrumentation_key
        )

    def test_export(self):
        """Test export."""
        record = MetricRecord(
            self._test_metric, self._test_labels, CounterAggregator()
        )
        exporter = LiveMetricsExporter(
            instrumentation_key=self._instrumentation_key,
            span_processor=self._span_processor,
        )
        with mock.patch(
            "azure_monitor.sdk.auto_collection.live_metrics.sender.LiveMetricsSender.post"
        ) as request:
            response = requests.Response()
            response.status_code = 200
            request.return_value = response
            result = exporter.export([record])
            self.assertEqual(result, MetricsExportResult.SUCCESS)

    def test_export_failed(self):
        record = MetricRecord(
            self._test_metric, self._test_labels, CounterAggregator()
        )
        exporter = LiveMetricsExporter(
            instrumentation_key=self._instrumentation_key,
            span_processor=self._span_processor,
        )
        with mock.patch(
            "azure_monitor.sdk.auto_collection.live_metrics.sender.LiveMetricsSender.post"
        ) as request:
            response = requests.Response()
            response.status_code = 400
            request.return_value = response
            result = exporter.export([record])
            self.assertEqual(result, MetricsExportResult.FAILURE)

    def test_export_exception(self):
        record = MetricRecord(
            self._test_metric, self._test_labels, CounterAggregator()
        )
        exporter = LiveMetricsExporter(
            instrumentation_key=self._instrumentation_key,
            span_processor=self._span_processor,
        )
        with mock.patch(
            "azure_monitor.sdk.auto_collection.live_metrics.sender.LiveMetricsSender.post",
            throw(Exception),
        ):
            result = exporter.export([record])
            self.assertEqual(result, MetricsExportResult.FAILURE)

    def test_live_metric_envelope_observer(self):
        aggregator = ValueObserverAggregator()
        aggregator.update(123)
        aggregator.take_checkpoint()
        record = MetricRecord(self._test_obs, self._test_labels, aggregator)
        exporter = LiveMetricsExporter(
            instrumentation_key=self._instrumentation_key,
            span_processor=self._span_processor,
        )

        envelope = exporter._metric_to_live_metrics_envelope([record])
        self.assertIsInstance(envelope, LiveMetricEnvelope)
        self.assertEqual(
            envelope.instrumentation_key,
            "99c42f65-1656-4c41-afde-bd86b709a4a7",
        )
        self.assertEqual(envelope.documents, [])
        self.assertEqual(envelope.metrics[0].name, "testname")
        self.assertEqual(envelope.metrics[0].value, 123)
        self.assertEqual(envelope.metrics[0].weight, 1)

    def test_live_metric_envelope_counter(self):
        aggregator = CounterAggregator()
        aggregator.update(123)
        aggregator.take_checkpoint()
        record = MetricRecord(self._test_metric, self._test_labels, aggregator)
        exporter = LiveMetricsExporter(
            instrumentation_key=self._instrumentation_key,
            span_processor=self._span_processor,
        )

        envelope = exporter._metric_to_live_metrics_envelope([record])
        self.assertIsInstance(envelope, LiveMetricEnvelope)
        self.assertEqual(envelope.documents, [])
        self.assertEqual(envelope.metrics[0].name, "testname")
        self.assertEqual(envelope.metrics[0].value, 123)
        self.assertEqual(envelope.metrics[0].weight, 1)

    def test_live_metric_envelope_value_recorder(self):
        aggregator = MinMaxSumCountAggregator()
        aggregator.update(123)
        aggregator.take_checkpoint()
        record = MetricRecord(
            self._test_metric2, self._test_labels, aggregator
        )
        exporter = LiveMetricsExporter(
            instrumentation_key=self._instrumentation_key,
            span_processor=self._span_processor,
        )

        envelope = exporter._metric_to_live_metrics_envelope([record])
        self.assertIsInstance(envelope, LiveMetricEnvelope)
        self.assertEqual(envelope.documents, [])
        self.assertEqual(envelope.metrics[0].name, "testname")
        self.assertEqual(envelope.metrics[0].value, 1)
        self.assertEqual(envelope.metrics[0].weight, 1)

    def test_live_metric_envelope_documents(self):
        aggregator = CounterAggregator()
        aggregator.update(123)
        aggregator.take_checkpoint()
        record = MetricRecord(self._test_metric, self._test_labels, aggregator)
        exporter = LiveMetricsExporter(
            instrumentation_key=self._instrumentation_key,
            span_processor=self._span_processor,
        )
        request_data = RemoteDependency(
            name="testName",
            id="",
            result_code="testResultCode",
            duration="testDuration",
            success=True,
            properties={},
            measurements={},
        )
        request_data.properties["test_property1"] = "test_property1Value"
        request_data.properties["test_property2"] = "test_property2Value"
        request_data.measurements[
            "test_measurement1"
        ] = "test_measurement1Value"
        request_data.measurements[
            "test_measurement2"
        ] = "test_measurement2Value"
        test_envelope = Envelope(
            data=Data(base_type="RemoteDependencyData", base_data=request_data)
        )
        self._span_processor.documents.append(test_envelope)
        envelope = exporter._metric_to_live_metrics_envelope([record])
        self.assertIsInstance(envelope, LiveMetricEnvelope)
        self.assertEqual(len(envelope.documents), 1)
        self.assertEqual(
            envelope.documents[0].quickpulse_type,
            "DependencyTelemetryDocument",
        )
        self.assertEqual(
            envelope.documents[0].document_type, "RemoteDependency"
        )
        self.assertEqual(envelope.documents[0].version, "1.0")
        self.assertEqual(envelope.documents[0].operation_id, "")
        self.assertEqual(len(envelope.documents[0].properties), 4)
        self.assertEqual(
            envelope.documents[0].properties["test_measurement1"],
            "test_measurement1Value",
        )
        self.assertEqual(
            envelope.documents[0].properties["test_measurement2"],
            "test_measurement2Value",
        )
        self.assertEqual(
            envelope.documents[0].properties["test_property1"],
            "test_property1Value",
        )
        self.assertEqual(
            envelope.documents[0].properties["test_property2"],
            "test_property2Value",
        )
