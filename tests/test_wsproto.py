# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

import unittest
import sys
from array import array
from os import path
from zope.interface import implements
from twisted.test.proto_helpers import MemoryReactor, StringTransport, AccumulatingProtocol


orig_name = __name__
orig_path = list(sys.path)
sys.path.insert(0, path.abspath(path.join(path.dirname(__file__), '..')))
try :
    devicehive = __import__('devicehive')
    __import__('devicehive.ws')
    ws = devicehive.ws
finally :
    sys.path[:] = orig_path
    __name__ = orig_name


class TestHandler(object):
    implements(ws.IWebSocketCallback)
    def __init__(self):
        self.payload = None
        self.connected = False
        self.closing = False
    def headers_received(self):
        self.connected = True
    def closing_connection(self):
        self.closing = True
    def frame_received(self, payload):
        self.payload = payload


class WebSocketProtocol13Test(unittest.TestCase):
    def test_send_frame(self):
        trans = StringTransport()
        proto = ws.WebSocketProtocol13(None, trans, 'localhost', '/test')
        proto.send_frame(True, 2, b'1234')
        data = trans.value()
        self.assertEquals(0x82, ord(data[0:1]))
        self.assertEquals(0x84, ord(data[1:2]))
        # test payload
        mask = data[2:6]
        pload = data[6:]
        unmasked = array('B', [ ord(pload[i]) ^ ord(mask[i % 4]) for i in range(len(pload))]).tostring()
        self.assertEquals(b'1234', unmasked)
    
    def test_receive_frame(self):
        trans = StringTransport()
        handler = TestHandler()
        proto = ws.WebSocketProtocol13(handler, trans, 'localhost', '/test')
        proto.security_key = b'dGhlIHNhbXBsZSBub25jZQ=='
        data  = u'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=\r\n\r\n'.encode('utf-8')
        data += b'\x81\x03\x01\x02\x03'
        proto.dataReceived(data)
        self.assertEquals(b'\x01\x02\x03', handler.payload)
    
    def test_invalid_opcode(self):
        trans = StringTransport()
        handler = TestHandler()
        proto = ws.WebSocketProtocol13(handler, trans, 'localhost', '/test')
        proto.security_key = b'dGhlIHNhbXBsZSBub25jZQ=='
        data  = u'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=\r\n\r\n'.encode('utf-8')
        data += b'\x83\x03\x01\x02\x03'
        try :
            proto.dataReceived(data)
            self.fail('Opcode 3 should raises an exception.')
        except ws.WebSocketError :
            pass
    
    def test_closing_connection(self):
        trans = StringTransport()
        handler = TestHandler()
        proto = ws.WebSocketProtocol13(handler, trans, 'localhost', '/test')
        proto.security_key = b'dGhlIHNhbXBsZSBub25jZQ=='
        data  = u'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=\r\n\r\n'.encode('utf-8')
        data += b'\x88\x00'
        proto.dataReceived(data)
        self.assertTrue(handler.closing)
    
    def test_invalid_sec_key(self):
        trans = StringTransport()
        handler = TestHandler()
        proto = ws.WebSocketProtocol13(handler, trans, 'localhost', '/test')
        proto.security_key = b'dGhlIHNhbXBsZSBub25jZQ=='
        data  = u'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: s2pPLMBiTxaQ9kYGzzhZRbK+xOo=\r\n\r\n'.encode('utf-8')
        try :
            proto.dataReceived(data)
            self.fail('Invalid security key should results in exception')
        except ws.WebSocketError:
            pass


if __name__ == '__main__' :
    unittest.main()

