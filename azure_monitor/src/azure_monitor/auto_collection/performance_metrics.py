# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import logging

from opentelemetry.metrics import LabelSet, Meter
from opentelemetry.sdk.metrics import Gauge

import psutil

logger = logging.getLogger(__name__)
PROCESS = psutil.Process()


class PerformanceMetrics:
    def __init__(self, meter: Meter, label_set: LabelSet):
        self._meter = meter
        self._label_set = label_set
        # Create performance metrics
        cpu_metric = self._meter.create_metric(
            "\\Processor(_Total)\\% Processor Time",
            "Processor time as a percentage",
            "percentage",
            float,
            Gauge,
        )
        self._cpu_handle = cpu_metric.get_handle(self._label_set)

        memory_metric = self._meter.create_metric(
            "\\Memory\\Available Bytes",
            "Amount of available memory in bytes",
            "byte",
            int,
            Gauge,
        )
        self._memory_handle = memory_metric.get_handle(self._label_set)

        process_cpu_metric = self._meter.create_metric(
            "\\Process(??APP_WIN32_PROC??)\\% Processor Time",
            "Process CPU usage as a percentage",
            "percentage",
            float,
            Gauge,
        )
        self._process_cpu_handle = process_cpu_metric.get_handle(
            self._label_set
        )

        process_memory_metric = self._meter.create_metric(
            "\\Process(??APP_WIN32_PROC??)\\Private Bytes",
            "Amount of memory process has used in bytes",
            "byte",
            int,
            Gauge,
        )
        self._process_memory_handle = process_memory_metric.get_handle(
            self._label_set
        )

    def track(self) -> None:
        self._track_cpu()
        self._track_process_cpu()
        self._track_memory()
        self._track_process_memory()

    def _track_cpu(self) -> None:
        """ Track CPU time

        Processor time is defined as a float representing the current system
        wide CPU utilization minus idle CPU time as a percentage. Idle CPU
        time is defined as the time spent doing nothing. Return values range
        from 0.0 to 100.0 inclusive.
        """
        cpu_times_percent = psutil.cpu_times_percent()
        self._cpu_handle.set(100 - cpu_times_percent.idle)

    def _track_process_cpu(self) -> None:
        """ Track Process CPU time

        Returns a derived gauge for the CPU usage for the current process.
        Return values range from 0.0 to 100.0 inclusive.
        """
        try:
            # In the case of a process running on multiple threads on different
            # CPU cores, the returned value of cpu_percent() can be > 100.0. We
            # normalize the cpu process using the number of logical CPUs
            cpu_count = psutil.cpu_count(logical=True)
            self._process_cpu_handle.set(PROCESS.cpu_percent() / cpu_count)
        except Exception:
            logger.exception("Error handling get process cpu usage.")

    def _track_memory(self) -> None:
        """ Track Memory

         Available memory is defined as memory that can be given instantly to
        processes without the system going into swap.
        """
        self._memory_handle.set(psutil.virtual_memory().available)

    def _track_process_memory(self) -> None:
        """ Track Memory

         Available memory is defined as memory that can be given instantly to
        processes without the system going into swap.
        """
        try:
            self._process_memory_handle.set(PROCESS.memory_info().rss)
        except Exception:
            logger.exception("Error handling get process private bytes.")
