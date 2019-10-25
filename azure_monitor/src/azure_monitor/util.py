import locale
import os
import platform
import sys

from azure_monitor.protocol import BaseObject
from azure_monitor.version import __version__ as ext_version
from opentelemetry.sdk.version import __version__ as opentelemetry_version

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


class Options(BaseObject):
    _default = BaseObject(
        endpoint="https://dc.services.visualstudio.com/v2/track",
        instrumentation_key=os.getenv("APPINSIGHTS_INSTRUMENTATIONKEY", None),
        timeout=10.0,  # networking timeout in seconds
    )
