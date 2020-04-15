# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import time
import unittest
from unittest import mock

from opentelemetry import metrics
from opentelemetry.sdk.metrics import Counter, Measure, MeterProvider

from azure_monitor.sdk.auto_collection.live_metrics.manager import (
    LiveMetricsManager,
)


# pylint: disable=protected-access
class TestAutoCollection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        metrics.set_meter_provider(MeterProvider())
        cls._meter = metrics.get_meter(__name__)
        cls._test_metric = cls._meter.create_metric(
            "testname", "testdesc", "unit", int, Counter, ["environment"]
        )
        testing_labels = {"environment": "testing"}
        cls._test_metric.add(5, testing_labels)
        cls._instrumentation_key = "99c42f65-1656-4c41-afde-bd86b709a4a7"

    @classmethod
    def tearDownClass(cls):
        metrics._METER_PROVIDER = None

    def test_constructor(self):
        """Test the constructor."""
        # LiveMetricsManager(
        #     meter=self._meter, instrumentation_key=self._instrumentation_key
        # )
        # time.sleep(200)
        # self.assertEqual(True, False)
