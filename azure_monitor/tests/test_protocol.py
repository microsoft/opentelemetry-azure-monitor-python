# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import unittest

from azure_monitor import protocol

class TestProtocol(unittest.TestCase):
    def test_object(self):
        data = protocol.BaseObject()
        self.assertEqual(repr(data), '{}')
        data.foo = 1
        self.assertEqual(data.foo, 1)
        self.assertEqual(data['foo'], 1)
        data['bar'] = 2
        self.assertEqual(data.bar, 2)
        self.assertEqual(data['bar'], 2)
        self.assertRaises(KeyError, lambda: data['baz'])
        self.assertRaises(AttributeError, lambda: data.baz)

    def test_data(self):
        data = protocol.Data()
        self.assertIsNone(data.baseData)
        self.assertIsNone(data.baseType)

    def test_envelope(self):
        data = protocol.Envelope()
        self.assertEqual(data.ver, 1)

    def test_event(self):
        data = protocol.Event()
        self.assertEqual(data.ver, 2)

    def test_exception_data(self):
        data = protocol.ExceptionData()
        self.assertEqual(data.ver, 2)

    def test_message(self):
        data = protocol.Message()
        self.assertEqual(data.ver, 2)

    def test_remote_dependency(self):
        data = protocol.RemoteDependency()
        self.assertEqual(data.ver, 2)

    def test_request(self):
        data = protocol.Request()
        self.assertEqual(data.ver, 2)
