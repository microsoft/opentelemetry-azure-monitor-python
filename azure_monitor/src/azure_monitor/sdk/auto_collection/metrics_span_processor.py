# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import logging

from opentelemetry.trace import SpanKind
from opentelemetry.sdk.trace import Span, SpanProcessor

from azure_monitor.export import convert_span_to_envelope

logger = logging.getLogger(__name__)


class AzureMetricsSpanProcessor(SpanProcessor):
    """AzureMetricsSpanProcessor is an implementation of `SpanProcessor` used
    to generate Azure specific metrics, including dependencies/requests rate, average duration
    and failed dependencies/requests.
    """

    def __init__(self, exporter=None):
        self._exporter = exporter
        self.request_count = 0
        self.dependency_count = 0
        self.failed_request_count = 0
        self.failed_dependency_count = 0
        self.request_duration = 0
        self.dependency_duration = 0

    def on_start(self, span: Span) -> None:
        pass

    def on_end(self, span: Span) -> None:
        try:
            if span.kind == SpanKind.SERVER:
                self.request_count = self.request_count + 1
                self.request_duration = self.request_duration + (
                    span.end_time - span.start_time
                )
                if not span.status.is_ok:
                    self.failed_request_count = self.failed_request_count + 1
                    if self._exporter is not None:
                        self._exporter.add_document(
                            convert_span_to_envelope(span)
                        )
            elif span.kind == SpanKind.CLIENT:
                self.dependency_count = self.dependency_count + 1
                self.dependency_duration = self.dependency_duration + (
                    span.end_time - span.start_time
                )
                if not span.status.is_ok:
                    self.failed_dependency_count = (
                        self.failed_dependency_count + 1
                    )
                    if self._exporter is not None:
                        self._exporter.add_document(
                            convert_span_to_envelope(span)
                        )

        # pylint: disable=broad-except
        except Exception:
            logger.exception("Exception while processing Span.")

    def shutdown(self) -> None:
        pass
