# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os
import shutil
import unittest

from azure_monitor.export import BaseExporter
from azure_monitor.options import ExporterOptions
from azure_monitor.protocol import Data, Envelope


TEST_FOLDER = os.path.abspath(".test.exporter")


def setUpModule():
    os.makedirs(TEST_FOLDER)


def tearDownModule():
    shutil.rmtree(TEST_FOLDER)


# pylint: disable=W0212
class TestBaseExporter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ[
            "APPINSIGHTS_INSTRUMENTATIONKEY"
        ] = "1234abcd-5678-4efa-8abc-1234567890ab"

    def test_constructor(self):
        """Test the constructor."""
        base = BaseExporter(
            instrumentation_key="4321abcd-5678-4efa-8abc-1234567890ab",
            storage_maintenance_period=2,
            storage_max_size=3,
            storage_path=os.path.join(TEST_FOLDER, self.id()),
            storage_retention_period=4,
            timeout=5,
        )
        self.assertIsInstance(base.options, ExporterOptions)
        self.assertEqual(
            base.options.instrumentation_key,
            "4321abcd-5678-4efa-8abc-1234567890ab",
        )
        self.assertEqual(base.options.storage_maintenance_period, 2)
        self.assertEqual(base.options.storage_max_size, 3)
        self.assertEqual(base.options.storage_retention_period, 4)
        self.assertEqual(base.options.timeout, 5)
        self.assertEqual(
            base.options.storage_path, os.path.join(TEST_FOLDER, self.id())
        )

    def test_constructor_wrong_options(self):
        """Test the constructor with wrong options."""
        with self.assertRaises(TypeError):
            BaseExporter(something_else=6)

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
            envelope.data.base_type += "_world"

        base.add_telemetry_processor(callback_function)
        envelope = Envelope(data=Data(base_type="type1"))
        base.apply_telemetry_processors([envelope])
        self.assertEqual(envelope.data.base_type, "type1_world")

    def test_telemetry_processor_apply_multiple(self):
        base = BaseExporter()
        base._telemetry_processors = []

        def callback_function(envelope):
            envelope.data.base_type += "_world"

        def callback_function2(envelope):
            envelope.data.base_type += "_world2"

        base.add_telemetry_processor(callback_function)
        base.add_telemetry_processor(callback_function2)
        envelope = Envelope(data=Data(base_type="type1"))
        base.apply_telemetry_processors([envelope])
        self.assertEqual(envelope.data.base_type, "type1_world_world2")

    def test_telemetry_processor_apply_exception(self):
        base = BaseExporter()

        def callback_function(envelope):
            raise ValueError()

        def callback_function2(envelope):
            envelope.data.base_type += "_world2"

        base.add_telemetry_processor(callback_function)
        base.add_telemetry_processor(callback_function2)
        envelope = Envelope(data=Data(base_type="type1"))
        base.apply_telemetry_processors([envelope])
        self.assertEqual(envelope.data.base_type, "type1_world2")

    def test_telemetry_processor_apply_not_accepted(self):
        base = BaseExporter()

        def callback_function(envelope):
            return envelope.data.base_type == "type2"

        base.add_telemetry_processor(callback_function)
        envelope = Envelope(data=Data(base_type="type1"))
        envelope2 = Envelope(data=Data(base_type="type2"))
        envelopes = base.apply_telemetry_processors([envelope, envelope2])
        self.assertEqual(len(envelopes), 1)
        self.assertEqual(envelopes[0].data.base_type, "type2")
