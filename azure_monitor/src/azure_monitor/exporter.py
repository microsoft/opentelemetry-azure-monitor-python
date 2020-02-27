# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import logging

from azure_monitor import utils

logger = logging.getLogger(__name__)


class BaseExporter:
    def __init__(self, **options):
        self._telemetry_processors = []
        self.options = utils.Options(**options)

    def add_telemetry_processor(self, processor):
        """Adds telemetry processor to the collection.

        Telemetry processors will be called one by one before telemetry
        item is pushed for sending and in the order they were added.
        :param processor: The processor to add.
        """
        self._telemetry_processors.append(processor)

    def clear_telemetry_processors(self):
        """Removes all telemetry processors"""
        self._telemetry_processors = []

    def apply_telemetry_processors(self, envelopes):
        """Applies all telemetry processors in the order they were added.

        This function will return the list of envelopes to be exported after
        each processor has been run sequentially. Individual processors can
        throw exceptions and fail, but the applying of all telemetry processors
        will proceed (not fast fail). Processors also return True if envelope
        should be included for exporting, False otherwise.
        :param envelopes: The envelopes to apply each processor to.
        """
        filtered_envelopes = []
        for envelope in envelopes:
            accepted = True
            for processor in self._telemetry_processors:
                try:
                    if processor(envelope) is False:
                        accepted = False
                        break
                except Exception as ex:
                    logger.warning("Telemetry processor failed with: %s.", ex)
            if accepted:
                filtered_envelopes.append(envelope)
        return filtered_envelopes
