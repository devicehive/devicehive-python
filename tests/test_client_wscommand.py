# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

from unittest import TestCase
from devicehive.client.ws import WsCommand


class WsCommandCreateTestCase(TestCase):
    def test_dict_expected(self):
        self.assertRaises(TypeError, WsCommand.create, None)

    def test_parameters_defaults_to_tuple(self):
        cmd = WsCommand.create({'id': 1, 'command': 'test', })
        self.assertIsInstance(cmd.parameters, (tuple, list, ))

    def test_parameters_stored_in_attribute(self):
        expected_value = (1, 2, 3, )
        cmd = WsCommand.create({'id': 1, 'command': 'test', 'parameters': expected_value, })
        self.assertEqual(expected_value, cmd.parameters)

    def test_default_values_of_attributes(self):
        cmd = WsCommand.create({'id': 1, 'command': 'test', })
        self.assertIsNone(cmd.timestamp)
        self.assertIsNone(cmd.user_id)
        self.assertIsNone(cmd.lifetime)
        self.assertIsNone(cmd.flags)
        self.assertIsNone(cmd.status)
        self.assertIsNone(cmd.result)

    def test_timestamp_can_be_set(self):
        expected_timestamp = 1
        cmd = WsCommand.create({'id': 1, 'command': 'test', 'timestamp': expected_timestamp, })
        self.assertEqual(expected_timestamp, cmd.timestamp)

    def test_user_id_can_be_set(self):
        expected_user_id = 1
        cmd = WsCommand.create({'id': 1, 'command': 'test', 'userId': expected_user_id, })
        self.assertEqual(expected_user_id, cmd.user_id)

    def test_lifetime_can_be_set(self):
        expected_lifetime = 1
        cmd = WsCommand.create({'id': 1, 'command': 'test', 'lifetime': expected_lifetime, })
        self.assertEqual(expected_lifetime, cmd.lifetime)

    def test_flags_can_be_set(self):
        expected_flags = 1
        cmd = WsCommand.create({'id': 1, 'command': 'test', 'flags': expected_flags, })
        self.assertEqual(expected_flags, cmd.flags)

    def test_status_can_be_set(self):
        expected_status = 1
        cmd = WsCommand.create({'id': 1, 'command': 'test', 'status': expected_status, })
        self.assertEqual(expected_status, cmd.status)

    def test_result_can_be_set(self):
        expected_result = 1
        cmd = WsCommand.create({'id': 1, 'command': 'test', 'result': expected_result, })
        self.assertEqual(expected_result, cmd.result)

    def test_default_dict(self):
        command_name = 'test'

        cmd = WsCommand.create({'id': 1, 'command': command_name, })
        result = cmd.to_dict()

        self.assertDictEqual({'command': command_name, 'parameters': [], }, result)

    def test_can_serialize_attributes(self):
        command_name = 'test'
        lifetime = 1
        flags = 2

        cmd = WsCommand.create({'id': 1, 'command': command_name, 'lifetime': lifetime, 'flags': flags, })
        result = cmd.to_dict()

        self.assertDictEqual({
            'command': command_name,
            'parameters': [],
            'lifetime': lifetime,
            'flags': flags,
        }, result)
