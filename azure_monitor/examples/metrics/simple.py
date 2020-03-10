# # Copyright (c) Microsoft Corporation. All rights reserved.
# # Licensed under the MIT License.
# import time

# from azure_monitor import AzureMonitorMetricsExporter
# from opentelemetry import metrics
# from opentelemetry.sdk.metrics import Counter, MeterProvider
# from opentelemetry.sdk.metrics.export.controller import PushController

# metrics.set_preferred_meter_provider_implementation(lambda _: MeterProvider())
# meter = metrics.get_meter(__name__)
# exporter = AzureMonitorMetricsExporter(
#     connection_string="InstrumentationKey=<INSTRUMENTATION KEY HERE>"
# )
# controller = PushController(meter, exporter, 5)

# requests_counter = meter.create_metric(
#     name="requests",
#     description="number of requests",
#     unit="1",
#     value_type=int,
#     metric_type=Counter,
#     label_keys=("environment",),
# )

# testing_label_set = meter.get_label_set({"environment": "testing"})

# requests_counter.add(25, testing_label_set)
# time.sleep(100)
