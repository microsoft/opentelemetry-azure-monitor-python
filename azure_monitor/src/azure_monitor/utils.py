# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import locale
import os
import platform
import re
import sys
import threading
import time
from enum import Enum

from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.sdk.version import __version__ as opentelemetry_version


from azure_monitor.protocol import BaseObject
from azure_monitor.version import __version__ as ext_version

azure_monitor_context = {
    "ai.cloud.role": os.path.basename(sys.argv[0]) or "Python Application",
    "ai.cloud.roleInstance": platform.node(),
    "ai.device.id": platform.node(),
    "ai.device.locale": locale.getdefaultlocale()[0],
    "ai.device.osVersion": platform.version(),
    "ai.device.type": "Other",
    "ai.internal.sdkVersion": "py{}:ot{}:ext{}".format(
        platform.python_version(), opentelemetry_version, ext_version
    ),
}


def ns_to_duration(nanoseconds):
    value = (nanoseconds + 500000) // 1000000  # duration in milliseconds
    value, microseconds = divmod(value, 1000)
    value, seconds = divmod(value, 60)
    value, minutes = divmod(value, 60)
    days, hours = divmod(value, 24)
    return "{:d}.{:02d}:{:02d}:{:02d}.{:03d}".format(
        days, hours, minutes, seconds, microseconds
    )


INGESTION_ENDPOINT = "ingestionendpoint"
INSTRUMENTATION_KEY = "instrumentationkey"

# Validate UUID format
# Specs taken from https://tools.ietf.org/html/rfc4122
uuid_regex_pattern = re.compile(
    "^[0-9a-f]{8}-"
    "[0-9a-f]{4}-"
    "[1-5][0-9a-f]{3}-"
    "[89ab][0-9a-f]{3}-"
    "[0-9a-f]{12}$"
)


class ExportResult(Enum):
    SUCCESS = 0
    FAILED_RETRYABLE = 1
    FAILED_NOT_RETRYABLE = 2


def get_trace_export_result(result: ExportResult):
    if result == ExportResult.SUCCESS:
        return SpanExportResult.SUCCESS
    elif result == ExportResult.FAILED_RETRYABLE:
        return SpanExportResult.FAILED_RETRYABLE
    elif result == ExportResult.FAILED_NOT_RETRYABLE:
        return SpanExportResult.FAILED_NOT_RETRYABLE
    else:
        return None


class Options(BaseObject):

    __slots__ = (
        "connection_string",
        "endpoint",
        "instrumentation_key",
        "max_batch_size",
        "storage_maintenance_period",
        "storage_max_size",
        "storage_path",
        "storage_retention_period",
        "timeout",
    )

    def __init__(
        self,
        connection_string=None,
        endpoint="https://dc.services.visualstudio.com/v2/track",
        instrumentation_key=None,
        max_batch_size=100,
        storage_maintenance_period=60,
        storage_max_size=100 * 1024 * 1024,
        storage_path=os.path.join(
            os.path.expanduser("~"),
            ".opentelemetry",
            ".azure",
            os.path.basename(sys.argv[0]) or ".console",
        ),
        storage_retention_period=7 * 24 * 60 * 60,
        timeout=10.0,  # networking timeout in seconds
    ) -> None:
        self.connection_string = connection_string
        self.endpoint = endpoint
        self.instrumentation_key = instrumentation_key
        self.max_batch_size = max_batch_size
        self.storage_maintenance_period = storage_maintenance_period
        self.storage_max_size = storage_max_size
        self.storage_path = storage_path
        self.storage_retention_period = storage_retention_period
        self.timeout = timeout
        self._initialize()
        self._validate_instrumentation_key()

    def _initialize(self):
        code_cs = self._parse_connection_string(self.connection_string)
        code_ikey = self.instrumentation_key
        env_cs = self._parse_connection_string(
            os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
        )
        env_ikey = os.getenv("APPINSIGHTS_INSTRUMENTATIONKEY")

        # The priority of which value takes on the instrumentation key is:
        # 1. Key from explicitly passed in connection string
        # 2. Key from explicitly passed in instrumentation key
        # 3. Key from connection string in environment variable
        # 4. Key from instrumentation key in environment variable
        self.instrumentation_key = (
            code_cs.get(INSTRUMENTATION_KEY)
            or code_ikey
            or env_cs.get(INSTRUMENTATION_KEY)
            or env_ikey
        )
        # The priority of the ingestion endpoint is as follows:
        # 1. The endpoint explicitly passed in connection string
        # 2. The endpoint from the connection string in environment variable
        # 3. The default breeze endpoint
        endpoint = (
            code_cs.get(INGESTION_ENDPOINT)
            or env_cs.get(INGESTION_ENDPOINT)
            or "https://dc.services.visualstudio.com"
        )
        self.endpoint = endpoint + "/v2/track"

    def _validate_instrumentation_key(self):
        """Validates the instrumentation key used for Azure Monitor.
        An instrumentation key cannot be null or empty. An instrumentation key
        is valid for Azure Monitor only if it is a valid UUID.
        :param instrumentation_key: The instrumentation key to validate
        """
        if not self.instrumentation_key:
            raise ValueError("Instrumentation key cannot be none or empty.")
        match = uuid_regex_pattern.match(self.instrumentation_key)
        if not match:
            raise ValueError("Invalid instrumentation key.")

    def _parse_connection_string(self, connection_string):
        if connection_string is None:
            return {}
        try:
            pairs = connection_string.split(";")
            result = dict(s.split("=") for s in pairs)
            # Convert keys to lower-case due to case type-insensitive checking
            result = {key.lower(): value for key, value in result.items()}
        except Exception:
            raise ValueError("Invalid connection string")
        # Validate authorization
        auth = result.get("authorization")
        if auth is not None and auth.lower() != "ikey":
            raise ValueError("Invalid authorization mechanism")
        # Construct the ingestion endpoint if not passed in explicitly
        if result.get(INGESTION_ENDPOINT) is None:
            endpoint_suffix = ""
            location_prefix = ""
            suffix = result.get("endpointsuffix")
            if suffix is not None:
                endpoint_suffix = suffix
                # Get regional information if provided
                prefix = result.get("location")
                if prefix is not None:
                    location_prefix = prefix + "."
                endpoint = "https://{0}dc.{1}".format(
                    location_prefix, endpoint_suffix
                )
                result[INGESTION_ENDPOINT] = endpoint
            else:
                # Default to None if cannot construct
                result[INGESTION_ENDPOINT] = None
        return result


class PeriodicTask(threading.Thread):
    """Thread that periodically calls a given function.

    :type interval: int or float
    :param interval: Seconds between calls to the function.

    :type function: function
    :param function: The function to call.

    :type args: list
    :param args: The args passed in while calling `function`.

    :type kwargs: dict
    :param args: The kwargs passed in while calling `function`.
    """

    def __init__(self, interval, function, args=None, kwargs=None):
        super(PeriodicTask, self).__init__()
        self.interval = interval
        self.function = function
        self.args = args or []
        self.kwargs = kwargs or {}
        self.finished = threading.Event()

    def run(self):
        wait_time = self.interval
        while not self.finished.wait(wait_time):
            start_time = time.time()
            self.function(*self.args, **self.kwargs)
            elapsed_time = time.time() - start_time
            wait_time = max(self.interval - elapsed_time, 0)

    def cancel(self):
        self.finished.set()
