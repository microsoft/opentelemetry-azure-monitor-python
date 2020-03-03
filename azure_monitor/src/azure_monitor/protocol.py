# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.


class BaseObject:
    __slots__ = ()

    def __repr__(self):
        tmp = {}

        for key in self.__slots__:
            data = getattr(self, key, None)
            if isinstance(data, BaseObject):
                tmp[key] = repr(data)
            else:
                tmp[key] = data

        return repr(tmp)


class Data(BaseObject):
    __slots__ = ("base_data", "base_type")

    def __init__(self, base_data=None, base_type=None) -> None:
        self.base_data = base_data
        self.base_type = base_type

    def to_dict(self):
        return {
            "baseData": self.base_data.to_dict() if self.base_data else None,
            "baseType": self.base_type.to_dict() if self.base_type else None,
        }


class DataPoint(BaseObject):
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

    def to_dict(self):
        return {
            "ns": self.ns,
            "name": self.name,
            "kind": self.kind,
            "value": self.value,
            "count": self.count,
            "min": self.min,
            "max": self.max,
            "stdDev": self.std_dev,
        }


class Envelope(BaseObject):
    __slots__ = (
        "ver",
        "name",
        "time",
        "sample_rate",
        "seq",
        "ikey",
        "flags",
        "tags",
        "data",
    )

    def __init__(
        self,
        ver=1,
        name="",
        time="",
        sample_rate=None,
        seq=None,
        ikey=None,
        flags=None,
        tags=None,
        data=None,
    ) -> None:
        self.ver = ver
        self.name = name
        self.time = time
        self.sample_rate = sample_rate
        self.seq = seq
        self.ikey = ikey
        self.flags = flags
        self.tags = tags
        self.data = data

    def to_dict(self):
        return {
            "ver": self.ver,
            "name": self.name,
            "time": self.time,
            "sampleRate": self.sample_rate,
            "seq": self.seq,
            "iKey": self.ikey,
            "flags": self.flags,
            "tags": self.tags,
            "data": self.data.to_dict() if self.data else None,
            "baseType": self.data.base_type if self.data else None,
        }


class Event(BaseObject):
    __slots__ = ("ver", "name", "properties", "measurements")

    def __init__(self, ver=2, name="", properties=None, measurements=None):
        self.ver = ver
        self.name = name
        self.properties = properties
        self.measurements = measurements

    def to_dict(self):
        return {
            "ver": self.ver,
            "name": self.name,
            "properties": self.properties,
            "measurements": self.measurements,
        }


class ExceptionData(BaseObject):
    __slots__ = (
        "ver",
        "exceptions",
        "severity_level",
        "problem_id",
        "properties",
        "measurements",
    )

    def __init__(
        self,
        ver=2,
        exceptions=None,
        severity_level=None,
        problem_id=None,
        properties=None,
        measurements=None,
    ) -> None:
        if exceptions is None:
            exceptions = []
        self.ver = ver
        self.exceptions = exceptions
        self.severity_level = severity_level
        self.problem_id = problem_id
        self.properties = properties
        self.measurements = measurements

    def to_dict(self):
        return {
            "ver": self.ver,
            "exceptions": self.exceptions,
            "severityLevel": self.severity_level,
            "problemId": self.problem_id,
            "properties": self.properties,
            "measurements": self.measurements,
        }


class Message(BaseObject):
    __slots__ = (
        "ver",
        "message",
        "severity_level",
        "properties",
        "measurements",
    )

    def __init__(
        self,
        ver=2,
        message="",
        severity_level=None,
        properties=None,
        measurements=None,
    ) -> None:
        self.ver = ver
        self.message = message
        self.severity_level = severity_level
        self.properties = properties
        self.measurements = measurements

    def to_dict(self):
        return {
            "ver": self.ver,
            "message": self.message,
            "severityLevel": self.severity_level,
            "properties": self.properties,
            "measurements": self.measurements,
        }


class MetricData(BaseObject):
    __slots__ = ("ver", "metrics", "properties")

    def __init__(self, ver=2, metrics=None, properties=None) -> None:
        if metrics is None:
            metrics = []
        self.ver = ver
        self.metrics = metrics
        self.properties = properties

    def to_dict(self):
        return {
            "ver": self.ver,
            "metrics": self.metrics,
            "properties": self.properties,
        }


class RemoteDependency(BaseObject):
    __slots__ = (
        "ver",
        "name",
        "id",
        "result_code",
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
        result_code="",
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
        self.result_code = result_code
        self.duration = duration
        self.success = success
        self.data = data
        self.type = type
        self.target = target
        self.properties = properties
        self.measurements = measurements

    def to_dict(self):
        return {
            "ver": self.ver,
            "name": self.name,
            "id": self.id,
            "resultCode": self.result_code,
            "duration": self.duration,
            "success": self.success,
            "data": self.data,
            "type": self.type,
            "target": self.target,
            "properties": self.properties,
            "measurements": self.measurements,
        }


class Request(BaseObject):
    __slots__ = (
        "ver",
        "id",
        "duration",
        "response_code",
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
        response_code="",
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
        self.response_code = response_code
        self.success = success
        self.source = source
        self.name = name
        self.url = url
        self.properties = properties
        self.measurements = measurements

    def to_dict(self):
        return {
            "ver": self.ver,
            "id": self.id,
            "duration": self.duration,
            "responseCode": self.response_code,
            "success": self.success,
            "source": self.source,
            "name": self.name,
            "url": self.url,
            "properties": self.properties,
            "measurements": self.measurements,
        }
