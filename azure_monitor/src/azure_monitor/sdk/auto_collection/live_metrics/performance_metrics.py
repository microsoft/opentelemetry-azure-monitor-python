# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import logging
from typing import Dict

import psutil
from opentelemetry.metrics import Meter

logger = logging.getLogger(__name__)
PROCESS = psutil.Process()


class PerformanceLiveMetrics:
    """Starts auto collection of performance live metrics.

    Args:
        meter: OpenTelemetry Meter
        labels: Dictionary of labels
    """

    def __init__(self, meter: Meter, labels: Dict[str, str]):
        self._meter = meter
        self._labels = labels
        # Create performance metrics
        meter.register_observer(
            callback=self._track_commited_memory,
            name="\\Memory\\Committed Bytes",
            description="Amount of commited memory in bytes",
            unit="byte",
            value_type=int,
        )

    def _track_commited_memory(self, observer) -> None:
        """ Track Commited Memory

        Available commited memory is defined as total memory minus available memory.
        """
        observer.observe(
            psutil.virtual_memory().total - psutil.virtual_memory().available,
            self._labels,
        )
