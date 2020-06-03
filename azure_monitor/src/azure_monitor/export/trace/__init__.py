# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import json
import logging
from typing import Sequence
from urllib.parse import urlparse

from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.sdk.util import ns_to_iso_str
from opentelemetry.trace import Span, SpanKind
from opentelemetry.trace.status import StatusCanonicalCode

from azure_monitor import protocol, utils
from azure_monitor.export import (
    BaseExporter,
    convert_span_to_envelope,
    ExportResult,
    get_trace_export_result,
)

logger = logging.getLogger(__name__)


class AzureMonitorSpanExporter(BaseExporter, SpanExporter):
    """Azure Monitor span exporter for OpenTelemetry.

    Args:
        options: :doc:`export.options` to allow configuration for the exporter
    """

    def export(self, spans: Sequence[Span]) -> SpanExportResult:
        envelopes = list(map(self._span_to_envelope, spans))
        envelopes = list(
            map(
                lambda x: x.to_dict(),
                self._apply_telemetry_processors(envelopes),
            )
        )
        try:
            result = self._transmit(envelopes)
            if result == ExportResult.FAILED_RETRYABLE:
                self.storage.put(envelopes, result)
            if result == ExportResult.SUCCESS:
                # Try to send any cached events
                self._transmit_from_storage()
            return get_trace_export_result(result)
        except Exception:  # pylint: disable=broad-except
            logger.exception("Exception occurred while exporting the data.")
            return get_trace_export_result(ExportResult.FAILED_NOT_RETRYABLE)

    # pylint: disable=too-many-statements
    # pylint: disable=too-many-branches
    def _span_to_envelope(self, span: Span) -> protocol.Envelope:
        if not span:
            return None
        envelope = convert_span_to_envelope(span)
        envelope.ikey = self.options.instrumentation_key
        return envelope
