# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
# pylint: disable=import-error
# pylint: disable=no-member
# pylint: disable=no-name-in-module
import requests
from opentelemetry import trace
from opentelemetry.ext import http_requests
from opentelemetry.sdk.trace import TracerSource
from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor

from azure_monitor import AzureMonitorSpanExporter

trace.set_preferred_tracer_source_implementation(lambda T: TracerSource())

http_requests.enable(trace.tracer_source())
span_processor = SimpleExportSpanProcessor(
    AzureMonitorSpanExporter(instrumentation_key="<INSTRUMENTATION KEY HERE>")
)
trace.tracer_source().add_span_processor(span_processor)
tracer = trace.tracer_source().get_tracer(__name__)

with tracer.start_as_current_span("parent"):
    response = requests.get("https://azure.microsoft.com/", timeout=5)
