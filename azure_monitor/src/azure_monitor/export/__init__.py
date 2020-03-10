# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import json
import logging
import typing

import requests

from enum import Enum

from opentelemetry.sdk.metrics.export import MetricsExportResult
from opentelemetry.sdk.trace.export import SpanExportResult

from azure_monitor.options import ExporterOptions
from azure_monitor.protocol import Envelope
from azure_monitor.storage import LocalFileStorage


logger = logging.getLogger(__name__)


class ExportResult(Enum):
    SUCCESS = 0
    FAILED_RETRYABLE = 1
    FAILED_NOT_RETRYABLE = 2


class BaseExporter:
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
        :param processor: The processor to add.
        """
        self._telemetry_processors.append(processor)

    def clear_telemetry_processors(self) -> None:
        """Removes all telemetry processors"""
        self._telemetry_processors = []

    def apply_telemetry_processors(
        self, envelopes: typing.List[Envelope]
    ) -> typing.List[Envelope]:
        """Applies all telemetry processors in the order they were added.

        This function will return the list of envelopes to be exported after
        each processor has been run sequentially. Individual processors can
        throw exceptions and fail, but the applying of all telemetry processors
        will proceed (not fast fail). Processors also return True if envelope
        should be included for exporting, False otherwise.
        :param envelopes: The envelopes to apply each processor to.
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

    def _transmit(
        self, envelopes: typing.List[Envelope]
    ) -> utils.ExportResult:
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
                return utils.ExportResult.FAILED_RETRYABLE

            text = "N/A"
            data = None
            try:
                text = response.text
            except Exception as ex:  # noqa pylint: disable=broad-except
                logger.warning("Error while reading response body %s.", ex)
            else:
                try:
                    data = json.loads(text)
                except Exception:  # noqa pylint: disable=broad-except
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
    elif result == ExportResult.FAILED_RETRYABLE:
        return SpanExportResult.FAILED_RETRYABLE
    elif result == ExportResult.FAILED_NOT_RETRYABLE:
        return SpanExportResult.FAILED_NOT_RETRYABLE
    else:
        return None


def get_metrics_export_result(result: ExportResult) -> MetricsExportResult:
    if result == ExportResult.SUCCESS:
        return MetricsExportResult.SUCCESS
    elif result == ExportResult.FAILED_RETRYABLE:
        return MetricsExportResult.FAILED_RETRYABLE
    elif result == ExportResult.FAILED_NOT_RETRYABLE:
        return MetricsExportResult.FAILED_NOT_RETRYABLE
    else:
        return None
