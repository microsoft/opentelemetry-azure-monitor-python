# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import locale
import os
import platform
import sys


from opentelemetry.sdk.version import __version__ as opentelemetry_version
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


class Options:
    __slots__ = ("endpoint", "instrumentation_key", "timeout")

    def __init__(
        self,
        endpoint="https://dc.services.visualstudio.com/v2/track",
        instrumentation_key=os.getenv("APPINSIGHTS_INSTRUMENTATIONKEY", None),
        timeout=10.0,  # networking timeout in seconds
    ) -> None:
        self.endpoint = endpoint
        self.instrumentation_key = instrumentation_key
        self.timeout = timeout
