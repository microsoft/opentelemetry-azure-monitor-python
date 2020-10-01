# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import requests
import time
from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchExportSpanProcessor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

from azure_monitor import AzureMonitorMetricsExporter, AzureMonitorSpanExporter

metrics.set_meter_provider(MeterProvider(stateful=False))

RequestsInstrumentor().instrument()
meter = RequestsInstrumentor().meter

exporter = AzureMonitorMetricsExporter(
    # connection_string="InstrumentationKey=<INSTRUMENTATION KEY HERE>"
)

metrics.get_meter_provider().start_pipeline(meter, exporter, 5)

# exporter = AzureMonitorSpanExporter(
#     # connection_string="InstrumentationKey=<INSTRUMENTATION KEY HERE>"
# )   

# trace.set_tracer_provider(TracerProvider())
# tracer = trace.get_tracer(__name__)
# span_processor = BatchExportSpanProcessor(exporter, schedule_delay_millis=2000)
# trace.get_tracer_provider().add_span_processor(span_processor)

for i in range(10):
    for x in range(10):
        requests.get('http://example.com')
        time.sleep(2)
    time.sleep(5)

input("Press any key to exit...")
