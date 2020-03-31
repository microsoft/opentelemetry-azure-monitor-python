# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
# pylint: disable=import-error
# pylint: disable=no-member
# pylint: disable=no-name-in-module
import requests
from opentelemetry import trace
from opentelemetry.ext import http_requests
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

from azure_monitor import AzureMonitorSpanExporter

trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)
http_requests.enable(trace.get_tracer_provider())
span_processor = BatchExportSpanProcessor(
    AzureMonitorSpanExporter(
        connection_string="InstrumentationKey=<INSTRUMENTATION KEY HERE>"
    )
)
trace.get_tracer_provider().add_span_processor(span_processor)

response = requests.get(url="http://google.com")

input("Press any key to exit...")
