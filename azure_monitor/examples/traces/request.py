# # Copyright (c) Microsoft Corporation. All rights reserved.
# # Licensed under the MIT License.
# # pylint: disable=import-error
# # pylint: disable=no-member
# # pylint: disable=no-name-in-module
# import requests
# from opentelemetry import trace
# from opentelemetry.ext import http_requests
# from opentelemetry.sdk.trace import TracerProvider
# from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor

# from azure_monitor import AzureMonitorSpanExporter

# trace.set_preferred_tracer_provider_implementation(lambda T: TracerProvider())

# http_requests.enable(trace.tracer_provider())
# span_processor = SimpleExportSpanProcessor(
#     AzureMonitorSpanExporter(
#         connection_string="InstrumentationKey=<INSTRUMENTATION KEY HERE>"
#     )
# )
# trace.tracer_provider().add_span_processor(span_processor)
# tracer = trace.get_tracer(__name__)

# with tracer.start_as_current_span("parent"):
#     response = requests.get("https://azure.microsoft.com/", timeout=5)
