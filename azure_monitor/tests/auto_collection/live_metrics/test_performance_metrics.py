# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import collections
import unittest
from unittest import mock

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider, Observer

from azure_monitor.sdk.auto_collection.live_metrics import (
    PerformanceLiveMetrics,
)


def throw(exc_type, *args, **kwargs):
    def func(*_args, **_kwargs):
        raise exc_type(*args, **kwargs)

    return func


# pylint: disable=protected-access
class TestPerformanceLiveMetrics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        metrics.set_meter_provider(MeterProvider())
        cls._meter = metrics.get_meter(__name__)
        cls._test_labels = {"environment": "staging"}

    @classmethod
    def tearDownClass(cls):
        metrics._METER_PROVIDER = None

    def test_constructor(self):
        mock_meter = mock.Mock()
        performance_metrics_collector = PerformanceLiveMetrics(
            meter=mock_meter, labels=self._test_labels
        )
        self.assertEqual(performance_metrics_collector._meter, mock_meter)
        self.assertEqual(
            performance_metrics_collector._labels, self._test_labels
        )
        self.assertEqual(mock_meter.register_observer.call_count, 1)
        reg_obs_calls = mock_meter.register_observer.call_args_list
        reg_obs_calls[0].assert_called_with(
            callback=performance_metrics_collector._track_commited_memory,
            name="\\Memory\\Committed Bytes",
            description="Amount of commited memory in bytes",
            unit="byte",
            value_type=int,
        )

    @mock.patch("psutil.virtual_memory")
    def test_track_memory(self, psutil_mock):
        performance_metrics_collector = PerformanceLiveMetrics(
            meter=self._meter, labels=self._test_labels
        )
        memory = collections.namedtuple("memory", ["available", "total"])
        vmem = memory(available=100, total=150)
        psutil_mock.return_value = vmem
        obs = Observer(
            callback=performance_metrics_collector._track_commited_memory,
            name="\\Memory\\Available Bytes",
            description="Amount of available memory in bytes",
            unit="byte",
            value_type=int,
            meter=self._meter,
        )
        performance_metrics_collector._track_commited_memory(obs)
        self.assertEqual(
            obs.aggregators[tuple(self._test_labels.items())].current, 50
        )
