# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

import sys
import os
import unittest
from random import Random
from zope.interface import implements
from twisted.python.failure import Failure
from twisted.internet.defer import Deferred
from twisted.test.proto_helpers import MemoryReactor, StringTransport, AccumulatingProtocol

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import devicehive
from devicehive.ws import WebSocketDeviceHiveProtocol, WebSocketError, WS_OPCODE_TEXT_FRAME
from devicehive.device.ws import WebSocketFactory, WS_STATE_WS_CONNECTED
from devicehive.interfaces import IProtoHandler


class Handler(object) :
    implements(IProtoHandler)
    
    factory = None
    
    def __init__(self):
        self.is_connected = False
    
    def on_connected(self):
        self.is_connected = True
    
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
        # tests what's happenning when there is a error
        defer = self.factory.send_message({'test': True})
        self.assertIsInstance(defer, Deferred)
        self.assertIsInstance(defer.result, Failure)
        self.assertIsInstance(defer.result.value, WebSocketError)
        # testing headers sending
        # this should result in connected event
        proto = self.factory.buildProtocol(None)
        proto.makeConnection(self.transport)
        origin = 'GET /device HTTP/1.1\r\n' + \
        'Host: localhost\r\n' + \
        'Upgrade: websocket\r\n' + \
        'Connection: Upgrade\r\n' + \
        'Sec-WebSocket-Key: {0}\r\n'.format(proto.socket.security_key) + \
        'Origin: http://localhost\r\n' + \
        'Sec-WebSocket-Protocol: device-hive, devicehive\r\n' + \
        'Sec-WebSocket-Version: 13\r\n\r\n'
        self.assertEquals(origin, self.transport.value())
        proto.dataReceived('HTTP/1.1 101 OK\r\n\r\n')
        self.assertTrue(self.handler.is_connected)
        self.transport.clear()
        # testing message sending
        self.factory.state = WS_STATE_WS_CONNECTED
        proto.socket.rand = Random(1)
        defer = self.factory.send_message({'test': True})
        self.assertIsInstance(defer, Deferred)
        data = '\x81\x9e\x22\xd8\xc3\x41\x59\xfa\xb7\x24\x51\xac\xe1\x7b\x02\xac\xb1\x34\x47\xf4\xe3\x63\x50\xbd\xb2\x34\x47\xab\xb7\x08\x46\xfa\xf9\x61\x13\xa5'
        self.assertEquals(data, self.transport.value())
        self.assertFalse(defer.called)
        # testing message response
        proto.socket.frame_received(WS_OPCODE_TEXT_FRAME, '{"requestId":1,"done":1}')
        self.assertTrue(defer.called)


if __name__ == '__main__' :
    unittest.main()

