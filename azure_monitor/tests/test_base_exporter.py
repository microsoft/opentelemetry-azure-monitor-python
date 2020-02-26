# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import unittest

from azure_monitor.exporter import BaseExporter
from azure_monitor.protocol import Envelope

# pylint: disable=W0212
class TestBaseExporter(unittest.TestCase):
    def test_telemetry_processor_add(self):
        base = BaseExporter()
        base.add_telemetry_processor(lambda: True)
        self.assertEqual(len(base._telemetry_processors), 1)

    def test_telemetry_processor_clear(self):
        base = BaseExporter()
        base.add_telemetry_processor(lambda: True)
        self.assertEqual(len(base._telemetry_processors), 1)
        base.clear_telemetry_processors()
        self.assertEqual(len(base._telemetry_processors), 0)

    def test_telemetry_processor_apply(self):
        base = BaseExporter()

        def callback_function(envelope):
            envelope.base_type += "_world"

        base.add_telemetry_processor(callback_function)
        envelope = Envelope()
        envelope.base_type = "type1"
        base.apply_telemetry_processors([envelope])
        self.assertEqual(envelope.base_type, "type1_world")

    def test_telemetry_processor_apply_multiple(self):
        base = BaseExporter()
        base._telemetry_processors = []

        def callback_function(envelope):
            envelope.base_type += "_world"

        def callback_function2(envelope):
            envelope.base_type += "_world2"

        base.add_telemetry_processor(callback_function)
        base.add_telemetry_processor(callback_function2)
        envelope = Envelope()
        envelope.base_type = "type1"
        base.apply_telemetry_processors([envelope])
        self.assertEqual(envelope.base_type, "type1_world_world2")

    def test_telemetry_processor_apply_exception(self):
        base = BaseExporter()

        def callback_function(envelope):
            raise ValueError()

        def callback_function2(envelope):
            envelope.base_type += "_world2"

        base.add_telemetry_processor(callback_function)
        base.add_telemetry_processor(callback_function2)
        envelope = Envelope()
        envelope.base_type = "type1"
        base.apply_telemetry_processors([envelope])
        self.assertEqual(envelope.base_type, "type1_world2")

    def test_telemetry_processor_apply_not_accepted(self):
        base = BaseExporter()

        def callback_function(envelope):
            return envelope.base_type == "type2"

        base.add_telemetry_processor(callback_function)
        envelope = Envelope()
        envelope.base_type = "type1"
        envelope2 = Envelope()
        envelope2.base_type = "type2"
        envelopes = base.apply_telemetry_processors([envelope, envelope2])
        self.assertEqual(len(envelopes), 1)
        self.assertEqual(envelopes[0].base_type, "type2")
