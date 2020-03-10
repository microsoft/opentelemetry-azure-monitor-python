# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.


import json
import os
import shutil
import unittest
from unittest import mock

from opentelemetry import metrics
from opentelemetry.sdk.metrics import Gauge, Meter
from opentelemetry.sdk.metrics.export import MetricRecord, MetricsExportResult
from opentelemetry.sdk.metrics.export.aggregate import CounterAggregator
from opentelemetry.sdk.util import ns_to_iso_str

from azure_monitor.auto_collection import PerformanceMetrics


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
        """Test the constructor."""
        auto_collector = PerformanceMetrics(
            meter=self._meter, label_set=self._test_label_set
        )
        self.assertEqual(auto_collector._meter, self._meter)
        self.assertEqual(auto_collector._label_set, self._test_label_set)

        result_metric = list(self._meter.metrics)[0]
        self.assertIsInstance(result_metric, Gauge)
        self.assertEqual(
            result_metric.name, "\Processor(_Total)\% Processor Time"
        )
        self.assertEqual(
            result_metric.description, "Processor time as a percentage"
        )
        self.assertEqual(result_metric.unit, "percentage")
        self.assertEqual(result_metric.value_type, float)
        self.assertEqual(
            result_metric.get_handle(
                self._test_label_set
            ).aggregator.checkpoint,
            0,
        )
