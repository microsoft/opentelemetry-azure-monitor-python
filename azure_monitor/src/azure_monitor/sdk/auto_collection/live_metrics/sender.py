# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
#
import json
import logging
import time

import requests

from azure_monitor.protocol import LiveMetricEnvelope
from azure_monitor.sdk.auto_collection.live_metrics import utils

logger = logging.getLogger(__name__)


class LiveMetricsSender:
    """Live Metrics Sender

    Send HTTP requests to Live Metrics service
    """

    def __init__(self, instrumentation_key: str):
        self._instrumentation_key = instrumentation_key

    def ping(self, envelope: LiveMetricEnvelope):
        return self._send_request(json.dumps(envelope.to_dict()), "ping")

    def post(self, envelope: LiveMetricEnvelope):
        return self._send_request(json.dumps([envelope.to_dict()]), "post")

    def _send_request(self, data: str, request_type: str) -> requests.Response:
        try:
            url = "{0}/QuickPulseService.svc/{1}?ikey={2}".format(
                utils.DEFAULT_LIVEMETRICS_ENDPOINT,
                request_type,
                self._instrumentation_key,
            )
            response = requests.post(
                url=url,
                data=data,
                headers={
                    "Expect": "100-continue",
                    "Content-Type": "application/json; charset=utf-8",
                    utils.LIVE_METRICS_TRANSMISSION_TIME_HEADER: str(
                        round(time.time()) * 1000
                    ),
                },
            )
        except requests.exceptions.HTTPError as ex:
            logger.warning("Failed to send live metrics: %s.", ex)
            return ex.response
        return response
