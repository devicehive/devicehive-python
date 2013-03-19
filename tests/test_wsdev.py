# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

import sys
import os
import unittest
import struct
import json
from array import array
from random import Random
from zope.interface import implements
from twisted.python.failure import Failure
from twisted.internet.defer import Deferred
from twisted.test.proto_helpers import MemoryReactor, StringTransport, AccumulatingProtocol

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import devicehive
from devicehive.interfaces import IDeviceInfo
from devicehive.ws import WebSocketDeviceHiveProtocol, WebSocketError, WS_OPCODE_TEXT_FRAME
from devicehive.device.ws import WebSocketFactory
from devicehive.interfaces import IProtoHandler


def decode_ws_message(data):
    offset = 1
    l = struct.unpack_from('B', data, offset)[0]
    l = l & ~0x80
    if l == 126 :
        offset += 1
        l = struct.unpack_from('!H', data, offset)[0]
        offset += 2
    elif l == 127 :
        offset += 1
        l = struct.unpack_from('!Q', data, offset)[0]
        offset += 4
    else :
        offset += 1
    mask = struct.unpack_from('B' * 4, data, offset)
    offset += 4
    data = struct.unpack_from('B' * l, data, offset)
    msg = array('B', [data[i] ^ mask[i % 4] for i in range(len(data))]).tostring()
    return msg


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


class WsClientSendingTestCase(unittest.TestCase):
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
        proto.socket.rand = Random(1)
        defer = self.factory.send_message({'test': True})
        self.assertIsInstance(defer, Deferred)
        self.assertEquals('{{"test": true, "requestId": {0}}}'.format(max(proto.msg_callbacks.keys())), decode_ws_message(self.transport.value()))
        self.assertFalse(defer.called)
        # testing message response
        request_id = max(proto.msg_callbacks.keys())
        proto.socket.frame_received(WS_OPCODE_TEXT_FRAME, '{{"requestId":{0},"done":1}}'.format(request_id))
        self.assertTrue(defer.called)


class WsClientMethodsTestCase(unittest.TestCase):
    def setUp(self):
        self.transport = StringTransport()
        self.handler = Handler()
        self.factory = WebSocketFactory(self.handler)
        self.proto = self.factory.buildProtocol(None)
        self.proto.makeConnection(self.transport)
        self.proto.dataReceived('HTTP/1.1 101 OK\r\n\r\n')
        self.proto.socket.rand = Random(1)
        self.transport.clear()
    
    def test_notify(self):
        self.transport.clear()
        defer = self.factory.notify('nt', {'a':1,'b':2}, device_id='123', device_key='321')
        s = decode_ws_message(self.transport.value())
        self.assertEquals({u'action': u'notification/insert',
                           u'notification': {u'notification': u'nt',
                                             u'parameters': {u'a': 1, u'b': 2}},
                           u'deviceKey': u'321',
                           u'deviceId': u'123',
                           u'requestId': max(self.proto.msg_callbacks.keys())}, json.loads(s))
    
    def test_subscribe(self):
        self.transport.clear()
        defer = self.factory.subscribe('123', '321')
        s = decode_ws_message(self.transport.value())
        self.assertEquals({u'action': u'command/subscribe',
                           u'deviceId': u'123',
                           u'deviceKey': u'321',
                           u'requestId': max(self.proto.msg_callbacks.keys())}, json.loads(s))
    
    def test_unsubscribe(self):
        self.transport.clear()
        defer = self.factory.unsubscribe('123', '312')
        s = decode_ws_message(self.transport.value())
        self.assertEquals({u'action': u'command/unsubscribe',
                           u'deviceKey': u'312',
                           u'deviceId': u'123',
                           u'requestId': max(self.proto.msg_callbacks.keys())}, json.loads(s))
    
    def test_authenticate(self):
        self.transport.clear()
        defer = self.factory.authenticate('123', '321')
        s = decode_ws_message(self.transport.value())
        self.assertEquals({u'action': u'authenticate',
                           u'deviceId': u'123',
                           u'deviceKey': u'321',
                           u'requestId': max(self.proto.msg_callbacks.keys())}, json.loads(s))
    
    def test_device_save(self):
        class TestDev(object):
            implements(IDeviceInfo)
            id = 'td_id'
            key = 'td_key'
            name = 'td_name'
            equipment = []
            status = None
            network = None
            device_class = None
        self.transport.clear()
        # minimal message
        info = TestDev()
        self.factory.device_save(info)
        s = decode_ws_message(self.transport.value())
        self.assertEquals({u'action': u'device/save',
                           u'device':
                                {u'equipment': [],
                                 u'name': u'td_name',
                                 u'key': u'td_key'},
                            u'deviceKey': u'td_key',
                            u'deviceId': u'td_id',
                            u'requestId': max(self.proto.msg_callbacks.keys())}, json.loads(s))
        # with equipment
        self.transport.clear()
        info.equipment = [devicehive.Equipment(name = 'en', code='cd', type='tp', data = None)]
        self.factory.device_save(info)
        s = decode_ws_message(self.transport.value())
        self.assertEquals({u'action': u'device/save',
                           u'device':
                                {u'equipment': [{u'name': u'en', u'code': u'cd', u'type': u'tp'}],
                                 u'name': u'td_name',
                                 u'key': u'td_key'},
                            u'deviceKey': u'td_key',
                            u'deviceId': u'td_id',
                            u'requestId': max(self.proto.msg_callbacks.keys())}, json.loads(s))
        # equipment with data
        self.transport.clear()
        info.equipment = [devicehive.Equipment(name = 'en', code='cd', type='tp', data = 'dt')]
        self.factory.device_save(info)
        s = decode_ws_message(self.transport.value())
        self.assertEquals({u'action': u'device/save',
                           u'device':
                                {u'equipment': [{u'name': u'en', u'code': u'cd', u'type': u'tp', u'data': u'dt'}],
                                 u'name': u'td_name',
                                 u'key': u'td_key'},
                            u'deviceKey': u'td_key',
                            u'deviceId': u'td_id',
                            u'requestId': max(self.proto.msg_callbacks.keys())}, json.loads(s))
        # with network
        self.transport.clear()
        info.network = devicehive.Network(id = 'nid', key = 'nkey', name = 'nname', descr = 'ndesr')
        self.factory.device_save(info)
        s = decode_ws_message(self.transport.value())
        self.assertEquals({u'action': u'device/save',
                           u'device':
                                {u'equipment': [{u'name': u'en', u'code': u'cd', u'type': u'tp', u'data': u'dt'}],
                                 u'name': u'td_name',
                                 u'key': u'td_key',
                                 u'network': {u'id': u'nid',
                                              u'name': u'nname',
                                              u'key': u'nkey',
                                              u'description': 'ndesr'}},
                            u'deviceKey': u'td_key',
                            u'deviceId': u'td_id',
                            u'requestId': max(self.proto.msg_callbacks.keys())}, json.loads(s))
        # end device_save


if __name__ == '__main__' :
    unittest.main()

