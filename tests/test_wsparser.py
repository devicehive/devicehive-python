# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

import unittest
import sys
from os import path
from zope.interface import implements


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


class WsHandler(object):
    implements(ws.IWebSocketParserCallback)
    
    def __init__(self):
        self.proto_version = ''
        self.code = 0
        self.status = ''
        self.frame = None
        self.headers = []
    
    def status_received(self, proto_version, code, status) :
        self.proto_version = proto_version
        self.code = code
        self.status = status
    
    def header_received(self, name, value):
        self.headers.append((name, value))
    
    def headers_received(self) :
        pass
    
    def frame_received(self, opcode, payload):
        self.frame = (opcode, payload)


class WebSocketParserTest(unittest.TestCase) :
    def test_headers(self):
        data  = u'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=\r\n\r\n'.encode('utf-8')
        handler = WsHandler()
        parser = ws.WebSocketParser(handler)
        parser.dataReceived(data)
        self.assertEquals('HTTP/1.1', handler.proto_version)
        self.assertEquals(101, handler.code)
        self.assertEquals([('Upgrade', 'websocket'), ('Connection', 'Upgrade'), ('Sec-WebSocket-Accept', 's3pPLMBiTxaQ9kYGzzhZRbK+xOo=')], handler.headers)
    
    def test_len7(self):
        data  = u'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=\r\n\r\n'.encode('utf-8')
        data += b'\x83\x03\x01\x02\x03'
        #
        handler = WsHandler()
        parser = ws.WebSocketParser(handler)
        parser.dataReceived(data)
        #
        self.assertEquals('HTTP/1.1', handler.proto_version)
        self.assertEquals(101, handler.code)
        self.assertEquals(0x03, handler.frame[0])
        self.assertEquals(b'\x01\x02\x03', handler.frame[1])
    
    def test_len16(self):
        data  = u'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=\r\n\r\n'.encode('utf-8')
        data += b'\x83\x7e\x00\x03\x01\x02\x03'
        handler = WsHandler()
        parser = ws.WebSocketParser(handler)
        parser.dataReceived(data)
        self.assertEquals(101, handler.code)
        self.assertEquals(3, handler.frame[0])
        self.assertEquals(b'\x01\x02\x03', handler.frame[1])
    
    def test_len64(self):
        data  = u'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=\r\n\r\n'.encode('utf-8')
        data += b'\x82\x7f\x00\x00\x00\x00\x00\x00\x00\x04\x00\x01\x02\x03'
        handler = WsHandler()
        parser = ws.WebSocketParser(handler)
        parser.dataReceived(data)
        self.assertEquals(101, handler.code)
        self.assertEquals(2, handler.frame[0])
        self.assertEquals(4, len(handler.frame[1]))
    
    def test_masking(self):
        data  = u'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=\r\n\r\n'.encode('utf-8')
        data += b'\x83\x83\x01\x02\x03'
        handler = WsHandler()
        parser = ws.WebSocketParser(handler)
        try :
            parser.dataReceived(data)
            self.fail('Websocket server is not allowed to mask data')
        except ws.WebSocketError :
            pass
    
    def test_framing(self):
        data1  = u'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=\r\n\r\n'.encode('utf-8')
        data1 += b'\x03\x03\x01\x02\x03'
        data2  = b'\x83\x03\x04\x05\x06'
        handler = WsHandler()
        parser = ws.WebSocketParser(handler)
        parser.dataReceived(data1)
        self.assertEquals(None, handler.frame)
        parser.dataReceived(data2)
        self.assertEquals(b'\x01\x02\x03\x04\x05\x06', handler.frame[1]) 


if __name__ == '__main__' :
    unittest.main()

