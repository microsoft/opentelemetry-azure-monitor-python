# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import collections
import logging

from opentelemetry.sdk.trace import Span, SpanProcessor

from azure_monitor.export.trace import convert_span_to_envelope

logger = logging.getLogger(__name__)


class AzureMetricsSpanProcessor(SpanProcessor):
    """AzureMetricsSpanProcessor is an implementation of `SpanProcessor` used
    to generate documents for Live Metrics.
    """

    def __init__(self):
        self.is_collecting_documents = False
        self.documents = collections.deque()

    def on_start(self, span: Span) -> None:
        pass

    def on_end(self, span: Span) -> None:
        try:
            if self.is_collecting_documents:
                if not span.status.is_ok:
                    self.documents.append(convert_span_to_envelope(span))
        # pylint: disable=broad-except
        except Exception:
            logger.warning("Exception while processing Span.")

    def shutdown(self) -> None:
        pass
