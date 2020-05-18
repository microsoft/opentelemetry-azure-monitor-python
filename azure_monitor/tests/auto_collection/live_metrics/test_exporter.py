# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import unittest
from unittest import mock

import requests
from opentelemetry import metrics
from opentelemetry.sdk.metrics import Counter, MeterProvider
from opentelemetry.sdk.metrics.export import MetricRecord, MetricsExportResult
from opentelemetry.sdk.metrics.export.aggregate import CounterAggregator

from azure_monitor.protocol import Envelope
from azure_monitor.sdk.auto_collection.live_metrics.exporter import (
    LiveMetricsExporter,
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
        cls._test_labels = tuple({"environment": "staging"}.items())

    def test_constructor(self):
        """Test the constructor."""
        exporter = LiveMetricsExporter(
            instrumentation_key=self._instrumentation_key
        )
        self.assertEqual(exporter.subscribed, True)
        self.assertEqual(
            exporter._instrumentation_key, self._instrumentation_key
        )

    def test_add_document(self):
        """Test adding a document."""
        exporter = LiveMetricsExporter(
            instrumentation_key=self._instrumentation_key
        )
        envelope = Envelope()
        exporter.add_document(envelope)
        self.assertEqual(exporter._document_envelopes.pop(), envelope)

    def test_export(self):
        """Test export."""
        record = MetricRecord(
            CounterAggregator(), self._test_labels, self._test_metric
        )
        exporter = LiveMetricsExporter(
            instrumentation_key=self._instrumentation_key
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
            CounterAggregator(), self._test_labels, self._test_metric
        )
        exporter = LiveMetricsExporter(
            instrumentation_key=self._instrumentation_key
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
            CounterAggregator(), self._test_labels, self._test_metric
        )
        exporter = LiveMetricsExporter(
            instrumentation_key=self._instrumentation_key
        )
        with mock.patch(
            "azure_monitor.sdk.auto_collection.live_metrics.sender.LiveMetricsSender.post",
            throw(Exception),
        ):
            result = exporter.export([record])
            self.assertEqual(result, MetricsExportResult.FAILURE)
