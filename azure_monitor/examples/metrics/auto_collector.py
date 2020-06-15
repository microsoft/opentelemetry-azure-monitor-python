# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export.controller import PushController
from opentelemetry.sdk.trace import TracerProvider

from azure_monitor import AzureMonitorMetricsExporter
from azure_monitor.sdk.auto_collection import (
    AutoCollection,
    AzureMetricsSpanProcessor,
)

# Add Span Processor to get metrics about traces
span_processor = AzureMetricsSpanProcessor()
tracer_provider = TracerProvider()
tracer_provider.add_span_processor(span_processor)
trace.set_tracer_provider(tracer_provider)

metrics.set_meter_provider(MeterProvider())
meter = metrics.get_meter(__name__)
exporter = AzureMonitorMetricsExporter(
    connection_string="InstrumentationKey=<INSTRUMENTATION KEY HERE>"
)
controller = PushController(meter, exporter, 5)

testing_label_set = {"environment": "testing"}

# Automatically collect standard metrics
auto_collection = AutoCollection(
    meter=meter, labels=testing_label_set, span_processor=span_processor
)

# To configure a separate export interval specific for standard metrics
# meter_standard = metrics.get_meter(__name__ + "_standard")
# controller _standard = PushController(meter_standard, exporter, 30)
# _auto_collection = AutoCollection(meter=meter_standard, label_set=testing_label_set)

input("Press any key to exit...")
