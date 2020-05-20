# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import unittest
from unittest import mock

from azure_monitor.protocol import LiveMetricEnvelope
from azure_monitor.sdk.auto_collection.live_metrics.sender import (
    LiveMetricsSender,
)


# pylint: disable=protected-access
class TestLiveMetricsSender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._instrumentation_key = "99c42f65-1656-4c41-afde-bd86b709a4a7"

    def test_constructor(self):
        """Test the constructor."""
        sender = LiveMetricsSender(
            instrumentation_key=self._instrumentation_key
        )
        self.assertEqual(
            sender._instrumentation_key, self._instrumentation_key
        )

    def test_ping(self):
        """Test ping."""
        sender = LiveMetricsSender(
            instrumentation_key=self._instrumentation_key
        )
        envelope = LiveMetricEnvelope()
        with mock.patch("requests.post") as request:
            sender.ping(envelope)
            self.assertTrue(request.called)
            self.assertEqual(
                request.call_args[1].get("url"),
                "https://rt.services.visualstudio.com/QuickPulseService.svc/ping?ikey={0}".format(
                    self._instrumentation_key
                ),
            )
            self.assertIsNotNone(request.call_args[1].get("data"))
            headers = request.call_args[1].get("headers")
            self.assertEqual(headers.get("Expect"), "100-continue")
            self.assertEqual(
                headers.get("Content-Type"), "application/json; charset=utf-8"
            )
            self.assertTrue(
                headers.get("x-ms-qps-transmission-time").isdigit()
            )

    def test_post(self):
        """Test post."""
        sender = LiveMetricsSender(
            instrumentation_key=self._instrumentation_key
        )
        envelope = LiveMetricEnvelope()
        with mock.patch("requests.post") as request:
            sender.post(envelope)
            self.assertTrue(request.called)
            self.assertEqual(
                request.call_args[1].get("url"),
                "https://rt.services.visualstudio.com/QuickPulseService.svc/post?ikey={0}".format(
                    self._instrumentation_key
                ),
            )
            self.assertIsNotNone(request.call_args[1].get("data"))
            headers = request.call_args[1].get("headers")
            self.assertEqual(headers.get("Expect"), "100-continue")
            self.assertEqual(
                headers.get("Content-Type"), "application/json; charset=utf-8"
            )
            self.assertTrue(
                headers.get("x-ms-qps-transmission-time").isdigit()
            )
