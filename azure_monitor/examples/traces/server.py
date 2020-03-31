# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
# pylint: disable=import-error
# pylint: disable=no-member
# pylint: disable=no-name-in-module
import requests
from opentelemetry import trace
from opentelemetry.ext import http_requests
from opentelemetry.ext.wsgi import OpenTelemetryMiddleware
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

import flask
from azure_monitor import AzureMonitorSpanExporter

# The preferred tracer implementation must be set, as the opentelemetry-api
# defines the interface with a no-op implementation.
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

exporter = AzureMonitorSpanExporter(
    connection_string="InstrumentationKey=<INSTRUMENTATION KEY HERE>"
)

# SpanExporter receives the spans and send them to the target location.
span_processor = BatchExportSpanProcessor(exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Integrations are the glue that binds the OpenTelemetry API and the
# frameworks and libraries that are used together, automatically creating
# Spans and propagating context as appropriate.
http_requests.enable(trace.get_tracer_provider())
app = flask.Flask(__name__)
app.wsgi_app = OpenTelemetryMiddleware(app.wsgi_app)


@app.route("/")
def hello():
    with tracer.start_as_current_span("parent"):
        requests.get("https://www.wikipedia.org/wiki/Rabbit")
    return "hello"


if __name__ == "__main__":
    app.run(host="localhost", port=8080, threaded=True)
