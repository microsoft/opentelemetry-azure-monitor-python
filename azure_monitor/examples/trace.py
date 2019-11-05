# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
from azure_monitor import AzureMonitorSpanExporter
from opentelemetry import trace
from opentelemetry.sdk.trace import Tracer
from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor

trace.set_preferred_tracer_implementation(lambda T: Tracer())
tracer = trace.tracer()
tracer.add_span_processor(
    SimpleExportSpanProcessor(AzureMonitorSpanExporter())
)

with tracer.start_as_current_span("hello") as span:
    print("Hello, World!")
