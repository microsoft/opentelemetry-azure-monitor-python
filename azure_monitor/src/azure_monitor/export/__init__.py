# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import json
import logging
import typing
from enum import Enum
from urllib.parse import urlparse

import requests
from opentelemetry.trace import Span, SpanKind
from opentelemetry.sdk.util import ns_to_iso_str
from opentelemetry.sdk.metrics.export import MetricsExportResult
from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.trace.status import StatusCanonicalCode

from azure_monitor import protocol, utils
from azure_monitor.options import ExporterOptions
from azure_monitor.protocol import Envelope
from azure_monitor.storage import LocalFileStorage

logger = logging.getLogger(__name__)


class ExportResult(Enum):
    SUCCESS = 0
    FAILED_RETRYABLE = 1
    FAILED_NOT_RETRYABLE = 2


# pylint: disable=broad-except
class BaseExporter:
    """Azure Monitor base exporter for OpenTelemetry.

    Args:
        options: :doc:`export.options` to allow configuration for the exporter
    """

    def __init__(self, **options):
        self._telemetry_processors = []
        self.options = ExporterOptions(**options)
        self.storage = LocalFileStorage(
            path=self.options.storage_path,
            max_size=self.options.storage_max_size,
            maintenance_period=self.options.storage_maintenance_period,
            retention_period=self.options.storage_retention_period,
        )

    def add_telemetry_processor(
        self, processor: typing.Callable[..., any]
    ) -> None:
        """Adds telemetry processor to the collection.

        Telemetry processors will be called one by one before telemetry
        item is pushed for sending and in the order they were added.

        Args:
            processor: Processor to add
        """
        self._telemetry_processors.append(processor)

    def clear_telemetry_processors(self) -> None:
        """Removes all telemetry processors"""
        self._telemetry_processors = []

    def _apply_telemetry_processors(
        self, envelopes: typing.List[Envelope]
    ) -> typing.List[Envelope]:
        """Applies all telemetry processors in the order they were added.

        This function will return the list of envelopes to be exported after
        each processor has been run sequentially. Individual processors can
        throw exceptions and fail, but the applying of all telemetry processors
        will proceed (not fast fail). Processors also return True if envelope
        should be included for exporting, False otherwise.

        Args:
            envelopes: The envelopes to apply each processor to.
        """
        filtered_envelopes = []
        for envelope in envelopes:
            accepted = True
            for processor in self._telemetry_processors:
                try:
                    if processor(envelope) is False:
                        accepted = False
                        break
                except Exception as ex:
                    logger.warning("Telemetry processor failed with: %s.", ex)
            if accepted:
                filtered_envelopes.append(envelope)
        return filtered_envelopes

    def _transmit_from_storage(self) -> None:
        for blob in self.storage.gets():
            # give a few more seconds for blob lease operation
            # to reduce the chance of race (for perf consideration)
            if blob.lease(self.options.timeout + 5):
                envelopes = blob.get()  # TODO: handle error
                result = self._transmit(envelopes)
                if result == ExportResult.FAILED_RETRYABLE:
                    blob.lease(1)
                else:
                    blob.delete(silent=True)

    # pylint: disable=too-many-branches
    # pylint: disable=too-many-nested-blocks
    def _transmit(self, envelopes: typing.List[Envelope]) -> ExportResult:
        """
        Transmit the data envelopes to the ingestion service.

        Returns an ExportResult, this function should never
        throw an exception.
        """
        if len(envelopes) > 0:
            try:
                response = requests.post(
                    url=self.options.endpoint,
                    data=json.dumps(envelopes),
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json; charset=utf-8",
                    },
                    timeout=self.options.timeout,
                )
            except Exception as ex:
                logger.warning("Transient client side error: %s.", ex)
                return ExportResult.FAILED_RETRYABLE

            text = "N/A"
            data = None
            try:
                text = response.text
            except Exception as ex:
                logger.warning("Error while reading response body %s.", ex)
            else:
                try:
                    data = json.loads(text)
                except Exception:
                    pass

            if response.status_code == 200:
                logger.info("Transmission succeeded: %s.", text)
                return ExportResult.SUCCESS
            if response.status_code == 206:  # Partial Content
                # TODO: store the unsent data
                if data:
                    try:
                        resend_envelopes = []
                        for error in data["errors"]:
                            if error["statusCode"] in (
                                429,  # Too Many Requests
                                439,  # Too Many Requests over extended time
                                500,  # Internal Server Error
                                503,  # Service Unavailable
                            ):
                                resend_envelopes.append(
                                    envelopes[error["index"]]
                                )
                            else:
                                logger.error(
                                    "Data drop %s: %s %s.",
                                    error["statusCode"],
                                    error["message"],
                                    envelopes[error["index"]],
                                )
                        if resend_envelopes:
                            self.storage.put(resend_envelopes)
                    except Exception as ex:
                        logger.error(
                            "Error while processing %s: %s %s.",
                            response.status_code,
                            text,
                            ex,
                        )
                    return ExportResult.FAILED_NOT_RETRYABLE
                # cannot parse response body, fallback to retry

            if response.status_code in (
                206,  # Partial Content
                429,  # Too Many Requests
                439,  # Too Many Requests over extended time
                500,  # Internal Server Error
                503,  # Service Unavailable
            ):
                return ExportResult.FAILED_RETRYABLE

            return ExportResult.FAILED_NOT_RETRYABLE
        # No spans to export
        return ExportResult.SUCCESS


def get_trace_export_result(result: ExportResult) -> SpanExportResult:
    if result == ExportResult.SUCCESS:
        return SpanExportResult.SUCCESS
    if result in (
        ExportResult.FAILED_RETRYABLE,
        ExportResult.FAILED_NOT_RETRYABLE,
    ):
        return SpanExportResult.FAILURE
    return None


def get_metrics_export_result(result: ExportResult) -> MetricsExportResult:
    if result == ExportResult.SUCCESS:
        return MetricsExportResult.SUCCESS
    if result in (
        ExportResult.FAILED_RETRYABLE,
        ExportResult.FAILED_NOT_RETRYABLE,
    ):
        return MetricsExportResult.FAILURE
    return None


# pylint: disable=too-many-statements
# pylint: disable=too-many-branches
def convert_span_to_envelope(span: Span) -> protocol.Envelope:
    if not span:
        return None
    envelope = protocol.Envelope(
        ikey="",
        tags=dict(utils.azure_monitor_context),
        time=ns_to_iso_str(span.start_time),
    )
    envelope.tags["ai.operation.id"] = "{:032x}".format(span.context.trace_id)
    parent = span.parent
    if isinstance(parent, Span):
        parent = parent.context
    if parent:
        envelope.tags["ai.operation.parentId"] = "{:016x}".format(
            parent.span_id
        )
    if span.kind in (SpanKind.CONSUMER, SpanKind.SERVER):
        envelope.name = "Microsoft.ApplicationInsights.Request"
        data = protocol.Request(
            id="{:016x}".format(span.context.span_id),
            duration=utils.ns_to_duration(span.end_time - span.start_time),
            response_code=str(span.status.canonical_code.value),
            success=span.status.canonical_code
            == StatusCanonicalCode.OK,  # Modify based off attributes or Status
            properties={},
        )
        envelope.data = protocol.Data(base_data=data, base_type="RequestData")
        if "http.method" in span.attributes:
            data.name = span.attributes["http.method"]
            if "http.route" in span.attributes:
                data.name = data.name + " " + span.attributes["http.route"]
                envelope.tags["ai.operation.name"] = data.name
                data.properties["request.name"] = data.name
            elif "http.path" in span.attributes:
                data.properties["request.name"] = (
                    data.name + " " + span.attributes["http.path"]
                )
        if "http.url" in span.attributes:
            data.url = span.attributes["http.url"]
            data.properties["request.url"] = span.attributes["http.url"]
        if "http.status_code" in span.attributes:
            status_code = span.attributes["http.status_code"]
            data.response_code = str(status_code)
            data.success = 200 <= status_code < 400
    else:
        envelope.name = "Microsoft.ApplicationInsights.RemoteDependency"
        data = protocol.RemoteDependency(
            name=span.name,
            id="{:016x}".format(span.context.span_id),
            result_code=str(span.status.canonical_code.value),
            duration=utils.ns_to_duration(span.end_time - span.start_time),
            success=span.status.canonical_code
            == StatusCanonicalCode.OK,  # Modify based off attributes or Status
            properties={},
        )
        envelope.data = protocol.Data(
            base_data=data, base_type="RemoteDependencyData"
        )
        if span.kind in (SpanKind.CLIENT, SpanKind.PRODUCER):
            if (
                "component" in span.attributes
                and span.attributes["component"] == "http"
            ):
                data.type = "HTTP"
            if "http.url" in span.attributes:
                url = span.attributes["http.url"]
                # data is the url
                data.data = url
                parse_url = urlparse(url)
                # TODO: error handling, probably put scheme as well
                # target matches authority (host:port)
                data.target = parse_url.netloc
                if "http.method" in span.attributes:
                    # name is METHOD/path
                    data.name = (
                        span.attributes["http.method"] + "/" + parse_url.path
                    )
            if "http.status_code" in span.attributes:
                status_code = span.attributes["http.status_code"]
                data.result_code = str(status_code)
                data.success = 200 <= status_code < 400
        else:  # SpanKind.INTERNAL
            data.type = "InProc"
            data.success = True
    for key in span.attributes:
        # This removes redundant data from ApplicationInsights
        if key.startswith("http."):
            continue
        data.properties[key] = span.attributes[key]
    if span.links:
        links = []
        for link in span.links:
            operation_id = "{:032x}".format(link.context.trace_id)
            span_id = "{:016x}".format(link.context.span_id)
            links.append({"operation_Id": operation_id, "id": span_id})
        data.properties["_MS.links"] = json.dumps(links)
    # TODO: tracestate, tags
    return envelope
