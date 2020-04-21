# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
#
import json
import logging
import time

import requests

from azure_monitor.protocol import LiveMetricEnvelope

DEFAULT_LIVEMETRICS_ENDPOINT = "https://rt.services.visualstudio.com"
LIVE_METRICS_TRANSMISSION_TIME_HEADER = "x-ms-qps-transmission-time"

logger = logging.getLogger(__name__)


class LiveMetricsSender:
    """Live Metrics Sender

    Send HTTP requests to Live Metrics service
    """

    def __init__(self, instrumentation_key: str):
        self._endpoint = DEFAULT_LIVEMETRICS_ENDPOINT
        self._instrumentation_key = instrumentation_key

    def ping(self, envelope: LiveMetricEnvelope):
        return self._send_request(json.dumps(envelope.to_dict()), "ping")

    def post(self, envelope: LiveMetricEnvelope):
        return self._send_request(json.dumps([envelope.to_dict()]), "post")

    def _send_request(self, data: str, request_type: str) -> requests.Response:
        try:
            url = "{0}/QuickPulseService.svc/{1}?ikey={2}".format(
                self._endpoint, request_type, self._instrumentation_key
            )
            response = requests.post(
                url=url,
                data=data,
                headers={
                    "Expect": "100-continue",
                    "Content-Type": "application/json; charset=utf-8",
                    LIVE_METRICS_TRANSMISSION_TIME_HEADER: str(
                        round(time.time()) * 1000
                    ),
                },
            )
        except Exception as ex:
            logger.warning("Failed to send live metrics: %s.", ex)
        return response
