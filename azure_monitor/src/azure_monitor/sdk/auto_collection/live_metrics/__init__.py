# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
#
import time
import typing
import uuid

from azure_monitor.protocol import BaseObject
from azure_monitor.utils import azure_monitor_context

LIVE_METRICS_SUBSCRIBED_HEADER = "x-ms-qps-subscribed"
STREAM_ID = str(uuid.uuid4())


def create_metric_envelope(instrumentation_key: str):
    envelope = LiveMetricEnvelope(
        documents=None,
        instance=azure_monitor_context.get("ai.cloud.roleInstance"),
        instrumentation_key=instrumentation_key,
        invariant_version=1,  # 1 -> v1 QPS protocol,
        machine_name=azure_monitor_context.get("ai.device.id"),
        metrics=None,
        stream_id=STREAM_ID,
        timestamp="/Date({0})/".format(str(int(time.time()) * 1000)),
        version=azure_monitor_context.get("ai.internal.sdkVersion"),
    )
    return envelope


class LiveMetricDocumentProperty(BaseObject):

    __slots__ = ("key", "value")

    def __init__(self, key: str, value: str) -> None:
        self.key = key
        self.value = value


class LiveMetricDocument(BaseObject):

    __slots__ = (
        "__type",
        "document_type",
        "version",
        "operation_id",
        "properties",
    )

    def __init__(
        self,
        __type: str = "",
        document_type: str = "",
        version: str = "",
        operation_id: str = "",
        properties: typing.List[LiveMetricDocumentProperty] = None,
    ) -> None:
        self.__type = __type
        self.document_type = document_type
        self.version = version
        self.operation_id = operation_id
        self.properties = properties

    def to_dict(self):
        return {
            "__type": self.__type,
            "DocumentType": self.document_type,
            "Version": self.version,
            "OperationId": self.operation_id,
            "Properties": self.properties.to_dict()
            if self.properties
            else None,
        }


class LiveMetric(BaseObject):

    __slots__ = ("name", "value", "weight")

    def __init__(self, name: str, value: str, weight: int) -> None:
        self.name = name
        self.value = value
        self.weight = weight

    def to_dict(self):
        return {"Name": self.name, "Value": self.value, "Weight": self.weight}


class LiveMetricEnvelope(BaseObject):
    """Envelope to send data to Live Metrics service.

    Args:
        documents: An array of detailed failure documents, each representing a full SDK telemetry item.
        instance: Instance name. Either a cloud RoleInstance (if running in Azure), or the machine name otherwise.
        instrumentation_key: Instrumentation key that the agent is instrumented with. While SDK can send to multiple ikeys,
        it must select a single ikey to send QuickPulse data to - and only consider telemetry items sent to that ikey while collecting.
        invariant_version: Version of QPS protocol that SDK supports. Currently, the latest is 2.
        machine_name: Machine name.
        metrics: Metrics
        stream_id: A random GUID generated at start-up. Must remain unchanged while the application is running.
        timestamp: UTC time the request was made in the Microsoft JSON format, e.g. "/Date(1478555534692)/".
        version: SDK version (not specific to QuickPulse). Please make sure that there's some sort of prefix to identify the client (.NET SDK, Java SDK, etc.).
    """

    __slots__ = (
        "documents",
        "instance",
        "instrumentation_key",
        "invariant_version",
        "machine_name",
        "metrics",
        "stream_id",
        "timestamp",
        "version",
    )

    def __init__(
        self,
        documents: typing.List[LiveMetricDocument] = None,
        instance: str = "",
        instrumentation_key: str = "",
        invariant_version: int = 1,
        machine_name: str = "",
        metrics: typing.List[LiveMetric] = None,
        stream_id: str = "",
        timestamp: str = "",
        version: str = "",
    ) -> None:
        if metrics is None:
            metrics = []
        self.documents = documents
        self.instance = instance
        self.instrumentation_key = instrumentation_key
        self.invariant_version = invariant_version
        self.machine_name = machine_name
        self.metrics = metrics
        self.stream_id = stream_id
        self.timestamp = timestamp
        self.version = version

    def to_dict(self):
        return {
            "Documents": self.documents.to_dict() if self.documents else None,
            "Instance": self.instance,
            "InstrumentationKey": self.instrumentation_key,
            "InvariantVersion": self.invariant_version,
            "MachineName": self.machine_name,
            "Metrics": list(map(lambda x: x.to_dict(), self.metrics)),
            "StreamId": self.stream_id,
            "Timestamp": self.timestamp,
            "Version": self.version,
        }
