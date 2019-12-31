# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
from azure_monitor import AzureMonitorSpanExporter
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerSource
from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor

trace.set_preferred_tracer_source_implementation(lambda T: TracerSource())
span_processor = SimpleExportSpanProcessor(
    AzureMonitorSpanExporter(instrumentation_key="<INSTRUMENTATION KEY HERE>")
)
trace.tracer_source().add_span_processor(span_processor)
tracer = trace.tracer_source().get_tracer(__name__)

with tracer.start_as_current_span("hello") as span:
    print("Hello, World!")
