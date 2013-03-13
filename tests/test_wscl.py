# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

import sys
import os
import unittest
from zope.interface import implements
from twisted.python.failure import Failure
from twisted.internet.defer import Deferred
from twisted.test.proto_helpers import MemoryReactor, StringTransport, AccumulatingProtocol

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import devicehive
from devicehive.ws import WebSocketDeviceHiveProtocol, WebSocketError
from devicehive.device.ws import WebSocketFactory
from devicehive.interfaces import IProtoHandler


class Handler(object) :
    implements(IProtoHandler)
    
    factory = None
    
    def on_apimeta(self, websocket_server, server_time):
        pass
    
    def on_connected(self):
        pass
    
    def on_connection_failed(self, reason):
        pass
    
    def on_closing_connection(self):
        pass
    
    def on_command(self, device_id, command, finished):
        pass
    
    def on_failure(self, device_id, reason):
        pass


class WsClientTestCase(unittest.TestCase):
    def setUp(self):
        self.transport = StringTransport()
        self.handler = Handler()
        self.factory = WebSocketFactory(self.handler)
    
    def test_buildProtocol(self):
        proto = self.factory.buildProtocol(None)
        self.assertIsInstance(proto, WebSocketDeviceHiveProtocol)
    
    def test_send_message(self):
        res = self.factory.send_message({'test': True})
        self.assertIsInstance(res, Deferred)
        self.assertIsInstance(res.result, Failure)
        self.assertIsInstance(res.result.value, WebSocketError)


if __name__ == '__main__' :
    unittest.main()

