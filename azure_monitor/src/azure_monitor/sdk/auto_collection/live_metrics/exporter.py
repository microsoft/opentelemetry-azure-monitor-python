# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
#
import collections
import logging
import typing

from opentelemetry.sdk.metrics import Counter, Observer
from opentelemetry.sdk.metrics.export import (
    MetricRecord,
    MetricsExporter,
    MetricsExportResult,
)

from azure_monitor.protocol import (
    Envelope,
    LiveMetric,
    LiveMetricDocument,
    LiveMetricDocumentProperty,
    LiveMetricEnvelope,
)
from azure_monitor.sdk.auto_collection import live_metrics
from azure_monitor.sdk.auto_collection.live_metrics.sender import (
    LiveMetricsSender,
)

logger = logging.getLogger(__name__)


class LiveMetricsExporter(MetricsExporter):
    """Live Metrics Exporter

    Export data to Azure Live Metrics service and determine if user is subscribed.
    """

    def __init__(self, instrumentation_key):
        self._instrumentation_key = instrumentation_key
        self._sender = LiveMetricsSender(self._instrumentation_key)
        self.subscribed = True
        self._document_envelopes = collections.deque()

    def add_document(self, envelope: Envelope):
        self._document_envelopes.append(envelope)

    def export(
        self, metric_records: typing.Sequence[MetricRecord]
    ) -> MetricsExportResult:
        envelope = self._metric_to_live_metrics_envelope(metric_records)
        try:
            response = self._sender.post(envelope)
            if response.ok:
                self.subscribed = (
                    response.headers.get(
                        live_metrics.LIVE_METRICS_SUBSCRIBED_HEADER
                    )
                    == "true"
                )
                return MetricsExportResult.SUCCESS

        except Exception:  # pylint: disable=broad-except
            logger.exception("Exception occurred while exporting the data.")

        return MetricsExportResult.FAILED_NOT_RETRYABLE

    def _metric_to_live_metrics_envelope(
        self, metric_records: typing.Sequence[MetricRecord]
    ) -> LiveMetricEnvelope:

        envelope = live_metrics.create_metric_envelope(
            self._instrumentation_key
        )
        envelope.documents = self._get_live_metric_documents()
        envelope.metrics = []

        # Add metrics
        for metric_record in metric_records:
            value = 0
            metric = metric_record.metric
            if isinstance(metric, Counter):
                value = metric_record.aggregator.checkpoint
            elif isinstance(metric, Observer):
                value = metric_record.aggregator.checkpoint.last
                if not value:
                    value = 0
            envelope.metrics.append(
                LiveMetric(name=metric.name, value=value, weight=1)
            )

        return envelope

    def _get_live_metric_documents(
        self,
    ) -> typing.Sequence[LiveMetricDocument]:
        live_metric_documents = []
        while self._document_envelopes:
            for envelope in self._document_envelopes.popleft():
                base_type = envelope.data.baseType
                if base_type:
                    document = LiveMetricDocument(
                        __type=self._get_live_metric_type(base_type),
                        document_type=self._get_live_metric_document_type(
                            base_type
                        ),
                        properties=self._get_aggregated_properties(envelope),
                        version="1.0",
                    )
                    live_metric_documents.append(document)
                else:
                    logger.warning(
                        "Document type invalid; not sending live metric document"
                    )

        return live_metric_documents

    def _get_live_metric_type(self, base_type: str) -> str:
        if base_type == "EventData":
            return "EventTelemetryDocument"
        elif base_type == "ExceptionData":
            return "ExceptionTelemetryDocument"
        elif base_type == "MessageData":
            return "TraceTelemetryDocument"
        elif base_type == "MetricData":
            return "MetricTelemetryDocument"
        elif base_type == "RequestData":
            return "RequestTelemetryDocument"
        elif base_type == "RemoteDependencyData":
            return "DependencyTelemetryDocument"
        elif base_type == "AvailabilityData":
            return "AvailabilityTelemetryDocument"

    def _get_live_metric_document_type(self, base_type: str) -> str:
        if base_type == "EventData":
            return "Event"
        elif base_type == "ExceptionData":
            return "Exception"
        elif base_type == "MessageData":
            return "Trace"
        elif base_type == "MetricData":
            return "Metric"
        elif base_type == "RequestData":
            return "Request"
        elif base_type == "RemoteDependencyData":
            return "RemoteDependency"
        elif base_type == "AvailabilityData":
            return "Availability"

    def _get_aggregated_properties(
        self, envelope: Envelope
    ) -> typing.List[LiveMetricDocumentProperty]:

        aggregated_properties = []
        measurements = (
            envelope.data.base_data.measurements
            if envelope.data.base_data.measurements
            else []
        )
        for key in measurements:
            prop = LiveMetricDocumentProperty(key=key, value=measurements[key])
            aggregated_properties.append(prop)
        properties = (
            envelope.data.base_data.properties
            if envelope.data.base_data.properties
            else []
        )
        for key in properties:
            prop = LiveMetricDocumentProperty(key=key, value=properties[key])
            aggregated_properties.append(prop)
        return aggregated_properties
