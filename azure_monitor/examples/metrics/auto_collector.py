# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider

from azure_monitor import AzureMonitorMetricsExporter
from azure_monitor.sdk.auto_collection import (
    AutoCollection,
    AzureMetricsSpanProcessor,
)

# Add Span Processor to get metrics about traces
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer_provider().get_tracer(__name__)
span_processor = AzureMetricsSpanProcessor()
trace.get_tracer_provider().add_span_processor(span_processor)

metrics.set_meter_provider(MeterProvider())
meter = metrics.get_meter(__name__)
exporter = AzureMonitorMetricsExporter(
    connection_string="InstrumentationKey=<INSTRUMENTATION KEY HERE>"
)

testing_label_set = {"environment": "testing"}

# Automatically collect standard metrics
auto_collection = AutoCollection(
    meter=meter, labels=testing_label_set, span_processor=span_processor
)

metrics.get_meter_provider().start_pipeline(meter, exporter, 2)

input("Press any key to exit...")
