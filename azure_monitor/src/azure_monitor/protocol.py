# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.


class Data:
    __slots__ = ("baseData", "baseType")

    def __init__(self, baseData=None, baseType=None) -> None:
        self.baseData = baseData
        self.baseType = baseType


class DataPoint:
    __slots__ = (
        "ns",
        "name",
        "kind",
        "value",
        "count",
        "min",
        "max",
        "std_dev",
    )

    def __init__(
        self,
        ns="",
        name="",
        kind=None,
        value=0.0,
        count=None,
        min=None,
        max=None,
        std_dev=None,
    ) -> None:
        self.ns = ns
        self.name = name
        self.kind = kind
        self.value = value
        self.count = count
        self.min = min
        self.max = max
        self.std_dev = std_dev


class Envelope:
    __slots__ = (
        "ver",
        "name",
        "time",
        "sampleRate",
        "seq",
        "iKey",
        "flags",
        "tags",
        "data",
    )

    def __init__(
        self,
        ver=1,
        name="",
        time="",
        sampleRate=None,
        seq=None,
        iKey=None,
        flags=None,
        tags=None,
        data=None,
    ) -> None:
        self.ver = ver
        self.name = name
        self.time = time
        self.sampleRate = sampleRate
        self.seq = seq
        self.iKey = iKey
        self.flags = flags
        self.tags = tags
        self.data = data


class Event:
    __slots__ = ("ver", "name", "properties", "measurements")

    def __init__(self, ver=2, name="", properties=None, measurements=None):
        self.ver = ver
        self.name = name
        self.properties = properties
        self.measurements = measurements


class ExceptionData:
    __slots__ = (
        "ver",
        "exceptions",
        "severityLevel",
        "problemId",
        "properties",
        "measurements",
    )

    def __init__(
        self,
        ver=2,
        exceptions=None,
        severityLevel=None,
        problemId=None,
        properties=None,
        measurements=None,
    ) -> None:
        if exceptions is None:
            exceptions = []
        self.ver = ver
        self.exceptions = exceptions
        self.severityLevel = severityLevel
        self.problemId = problemId
        self.properties = properties
        self.measurements = measurements


class Message:
    __slots__ = (
        "ver",
        "message",
        "severityLevel",
        "properties",
        "measurements",
    )

    def __init__(
        self,
        ver=2,
        message="",
        severityLevel=None,
        properties=None,
        measurements=None,
    ) -> None:
        self.ver = ver
        self.message = message
        self.severityLevel = severityLevel
        self.properties = properties
        self.measurements = measurements


class MetricData:
    __slots__ = ("ver", "metrics", "properties")

    def __init__(self, ver=2, metrics=None, properties=None) -> None:
        if metrics is None:
            metrics = []
        self.ver = ver
        self.metrics = metrics
        self.properties = properties


class RemoteDependency:
    __slots__ = (
        "ver",
        "name",
        "id",
        "resultCode",
        "duration",
        "success",
        "data",
        "type",
        "target",
        "properties",
        "measurements",
    )

    def __init__(
        self,
        ver=2,
        name="",
        id="",
        resultCode="",
        duration="",
        success=True,
        data=None,
        type=None,
        target=None,
        properties=None,
        measurements=None,
    ) -> None:
        self.ver = ver
        self.name = name
        self.id = id
        self.resultCode = resultCode
        self.duration = duration
        self.success = success
        self.data = data
        self.type = type
        self.target = target
        self.properties = properties
        self.measurements = measurements


class Request:
    __slots__ = (
        "ver",
        "id",
        "duration",
        "responseCode",
        "success",
        "source",
        "name",
        "url",
        "properties",
        "measurements",
    )

    def __init__(
        self,
        ver=2,
        id="",
        duration="",
        responseCode="",
        success=True,
        source=None,
        name=None,
        url=None,
        properties=None,
        measurements=None,
    ) -> None:
        self.ver = ver
        self.id = id
        self.duration = duration
        self.responseCode = responseCode
        self.success = success
        self.source = source
        self.name = name
        self.url = url
        self.properties = properties
        self.measurements = measurements

