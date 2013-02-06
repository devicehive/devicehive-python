# -*- encoding: utf8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8 encoding=utf-8


import json
import base64
import uuid
import sha
from functools import partial
from datetime import datetime
import struct
from time import time
from random import Random
from array import array
from zope.interface import implements, Interface
from twisted.python import log
from twisted.python.constants import Values, ValueConstant
from twisted.internet.protocol import ClientFactory, Protocol
from twisted.web.client import HTTP11ClientProtocol, Request
from twisted.internet.defer import Deferred
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor
from urlparse import urlsplit, urljoin
from devicehive import *


__all__ = ['WebSocketError', 'WebSocketDeviceHiveProtocol', 'WebSocketProtocol13']


class IProtoHandler(Interface):
    def authenticate(self):
        """
        """
    
    def notity(self, notification, *kwargs):
        """
        @returns deferred
        """
    
    def command_subscribe(self):
        """
        """
    
    def command_unsubscribe(self):
        """
        """
    
    def register_command(self):
        """
        """


class WebSocketError(Exception):
    def __init__(self, msg = '') :
        super(WebSocketError, self).__init__('WebSocket error. Reason: {0}.'.format(msg))


class IWebSocketProtocol13Handler(Interface):
    def headers_received(self) :
        """
        Indicates that from this point server and client could exchange data.
        """
        pass
    
    def frame_received(self, payload) :
        """
        Is called when a new frame is received.
        """
        pass
    
    def connection_closed(self):
        """
        Is called when server sends connection close request
        """
        pass


class IWebSocketHandler(Interface) :
    def status_received(self, proto_version, code, status) :
        pass
    
    def header_received(self, name, value):
        pass
    
    def headers_received(self) :
        pass
    
    def frame_received(self, opcode, payload):
        pass


WS_OPCODE_CONTINUATION = 0
WS_OPCODE_TEXT_FRAME   = 1
WS_OPCODE_BINARY_FRAME = 2
WS_OPCODE_CONNECTION_CLOSE = 8
WS_OPCODE_PING = 9
WS_OPCODE_PONG = 10


WS_GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'


class WebSocketState(Values) :
    Status     = ValueConstant(0)
    Header     = ValueConstant(1)
    WsHeader   = ValueConstant(2)
    WsLength7  = ValueConstant(3)
    WsLength16 = ValueConstant(4)
    WsLength64 = ValueConstant(5)
    WsPayload  = ValueConstant(6)


class WebSocketParser(LineReceiver) :
    """
    Class parses incoming byte stream and extracts HTTP headers and WebSocket frames.
    """
    
    def __init__(self, handler):
        self.state = WebSocketState.Status
        self.handler = handler
        # attribute to store header
        self._header_buf = None
        # attributes which store frame
        # data and parameters
        self._frame_buf = b''
        self._frame_fin = False
        self._frame_opcode = 0
        self._frame_len = 0
        self._frame_data = b''
    
    def lineReceived(self, line):
        if line[-1:] == '\r':
            line = line[:-1]
        
        if self.state == WebSocketState.Status :
            self.status_received(line)
            self.state = WebSocketState.Header
        elif self.state == WebSocketState.Header :
            if not line or line[0] not in ' \t':
                if self._header_buf is not None:
                    header = ''.join(self._header_buf)
                    name, value = header.split(':', 1)
                    value = value.strip()
                    self.header_received(name, value)
                
                if not line:
                    self.headers_received()
                else:
                    self._header_buf = [line]
            else:
                self._header_buf.append(line)
    
    def status_received(self, line) :
        if (self.handler is not None) and IWebSocketHandler.implementedBy(self.handler.__class__) :
            proto_version, code, status = line.split(' ', 2)
            self.handler.status_received(proto_version, int(code, 10), status)
    
    def header_received(self, name, value):
        if (self.handler is not None) and IWebSocketHandler.implementedBy(self.handler.__class__) :
            self.handler.header_received(name, value)
    
    def headers_received(self) :
        if (self.handler is not None) and IWebSocketHandler.implementedBy(self.handler.__class__) :
            self.handler.headers_received()
        self.state = WebSocketState.WsHeader
        self.setRawMode()
    
    def frame_received(self, opcode, payload):
        if (self.handler is not None) and IWebSocketHandler.implementedBy(self.handler.__class__) :
            self.handler.frame_received(opcode, payload)
    
    def rawDataReceived(self, data):
        self._frame_buf += data
        #
        while True :
            if self.state == WebSocketState.WsHeader :
                if len(self._frame_buf) > 0 :
                    hdr = struct.unpack('B', self._frame_buf[:1])[0]
                    self._frame_buf = self._frame_buf[1:]
                    self._frame_fin = (hdr & 0x80)
                    self._frame_opcode = (hdr & 0x0f)
                    self.state = WebSocketState.WsLength7
                else :
                    break
            elif self.state == WebSocketState.WsLength7 :
                if len(self._frame_buf) > 0 :
                    len7 = struct.unpack('B', self._frame_buf[:1])[0]
                    self._frame_buf = self._frame_buf[1:]
                    if len7 & 0x80 :
                        raise WebSocketError('Server should not mask websocket frames.')
                    else :
                        len7 = len7 & 0x7f
                        if len7 == 126 :
                            self._frame_len = 0
                            self.state = WebSocketState.WsLength16
                        elif len7 == 127 :
                            self._frame_len = 0
                            self.state = WebSocketState.WsLength64
                        else :
                            self._frame_len = len7
                            self.state = WebSocketState.WsPayload
                else :
                    break
            elif self.state == WebSocketState.WsLength16 :
                if len(self._frame_buf) > 1 :
                    len16 = struct.unpack('!H', self._frame_buf[:2])[0]
                    self._frame_buf = self._frame_buf[2:]
                    self._frame_len = len16
                    self.state = WebSocketState.WsPayload
                else :
                    break
            elif self.state == WebSocketState.WsLength64 :
                if len(self._frame_buf) > 7 :
                    len64 = struct.unpack('!Q', self._frame_buf[:8])[0]
                    self._frame_buf = self._frame_buf[8:]
                    self._frame_len = len64
                    self.state = WebSocketState.WsPayload
                else :
                    break
            elif self.state == WebSocketState.WsPayload :
                if self._frame_len == 0 :
                    if self._frame_fin :
                        self.frame_received(self._frame_opcode, self._frame_data)
                        self._frame_data = b''
                        self._frame_opcode = 0
                    self.state = WebSocketState.WsHeader
                elif len(self._frame_buf) == 0 :
                    break
                else :
                    bytes_to_read = min(self._frame_len, len(self._frame_buf))
                    self._frame_data += self._frame_buf[:bytes_to_read]
                    self._frame_buf = self._frame_buf[bytes_to_read:]
                    self._frame_len -= bytes_to_read
            elif self.state == WebSocketState.WsError :
                break
        pass


class WebSocketProtocol13(object):
    implements(IWebSocketHandler)
    
    def __init__(self, factory, handler, transport = None):
        self.factory = factory
        self.handler = handler
        self.transport = transport
        #
        self.security_key = base64.b64encode((uuid.uuid4()).bytes)
        self.rand = Random(long(time()))
        self.parser = WebSocketParser(self)
    
    def dataReceived(self, data):
        self.parser.dataReceived(data)
    
    def status_received(self, proto_version, code, status):
        if proto_version != 'HTTP/1.1' :
            raise WebSocketError('unsupported protocol {0}'.format(proto_version))
        if code != 101 :
            raise WebSocketError('websocket server rejected protocol upgrade with code {0}'.format(code))
    
    def header_received(self, name, value):
        loname = name.lower()
        if loname == 'sec-websocket-accept' :
            if not self.validate_security_answer(value) :
                raise WebSocketError('websocket server returned invalid security key {0} in response to {1}'.format(value, self.security_key))
        elif loname == 'connection' :
            if value.lower() != 'upgrade' :
                raise WebSocketError('websocket server failed to upgrade connection, status = {0}'.format(value))
        elif loname == 'upgrade' :
            if value.lower() != 'websocket' :
                raise WebSocketError('websocket server upgraded protocol to invalid state {0}'.format(value))
    
    def headers_received(self):
        if (self.handler is not None) and IWebSocketProtocol13Handler.implementedBy(self.handler.__class__) :
            self.handler.headers_received()
    
    def frame_received(self, opcode, payload):
        if opcode == WS_OPCODE_PING :
            self.send_frame(1, WS_OPCODE_PONG, payload)
        elif opcode == WS_OPCODE_CONNECTION_CLOSE :
            if (self.handler is not None) and IWebSocketProtocol13Handler.implementedBy(self.handler.__class__) :
                self.handler.connection_closed()
        elif opcode == WS_OPCODE_BINARY_FRAME or opcode == WS_OPCODE_TEXT_FRAME :
            if (self.handler is not None) and IWebSocketProtocol13Handler.implementedBy(self.handler.__class__) :
                self.handler.frame_received(payload)
        else :
            raise WebSocketError('opcode {0} is not supported'.format(opcode))
    
    def validate_security_answer(self, answer):
        skey = sha.new(self.security_key + WS_GUID)
        key = base64.b64encode(skey.digest())
        return answer == key
    
    def send_headers(self) :
        header = 'GET /device HTTP/1.1\r\n' + \
                  'Host: {0}\r\n' + \
                  'Auth-DeviceID: {1}\r\n' + \
                  'Auth-DeviceKey: {2}\r\n' + \
                  'Upgrade: websocket\r\n' + \
                  'Connection: Upgrade\r\n' + \
                  'Sec-WebSocket-Key: {3}' + \
                  'Origin: http://{0}\r\n' + \
                  'Sec-WebSocket-Protocol: device-hive, devicehive\r\n' + \
                  'Sec-WebSocket-Version: 13\r\n\r\n'
        return header.format(self.factory.host,
                             self.factory.device_delegate.device_id(),
                             self.factory.device_delegate.device_key(),
                             self.security_key).encode('utf-8')
    
    def send_frame(self, fin, opcode, data) :
        frame = struct.pack('B', (0x80 if fin else 0x00) | opcode)[0]
        l = len(data)
        if l < 126:
            frame += struct.pack('B', l | 0x80)[0]
        elif l <= 0xFFFF:
            frame += struct.pack('!BH', 126 | 0x80, l)[0]
        else:
            frame += struct.pack('!BQ', 127 | 0x80, l)[0]
        mask  = chr(self.rand.randint(0, 0xff)) + chr(self.rand.randint(0, 0xff)) + chr(self.rand.randint(0, 0xff)) + chr(self.rand.randint(0, 0xff))
        frame += mask
        frame += array('B', [ord(data[i]) ^ ord(mask[i % 4]) for i in range(len(data))]).tostring()
        self.transport.write(frame)


class WebSocketDeviceHiveProtocol(HTTP11ClientProtocol):
    """
    Implements Device-Hive protocol over WebSockets
    """
    
    implements(IWebSocketProtocol13Handler)
    
    def request_counter():
        request_number = 1
        while True :
            yield request_number
            request_number += 1
    request_counter = request_counter()
    
    def __init__(self, factory):
        if hasattr(HTTP11ClientProtocol, '__init__'):
            HTTP11ClientProtocol.__init__(self)
        self.factory = factory
        self.socket = WebSocketProtocol13(self.factory)
    
    def headers_received(self):
        self.authenticate()
    
    def frame_received(self, payload):
        message = json.loads(payload)
        if message['action'] == u'authenticate' :
            if message['status'] == u'success' :
                self.device_save()
            else :
                self.authenticate()
        elif message['action'] == u'device/get' :
            if message['status'] == u'success' :
                pass
            else :
                pass
        else :
            raise NotImplementedError()
    
    def connection_closed(self):
        self.factory.abort()
    
    def makeConnection(self, transport):
        self.socket.transport = transport
        return super(WebSocketDeviceHiveProtocol, self).makeConnection(transport)
    
    def connectionMade(self):
        if self.factory.state.value == ProtocolState.ApiMetadata :
            res = self.request(ApiMetadataRequest(self.factory))
            res.addCallbacks(self._apimetadata_done, self._critical_error)
        elif self.factory.state.value == ProtocolState.Register :
            self.factory.state = StateHolder(ProtocolState.Registering, self.state.data, self.state.retries)
            self.socket.send_headers()
        else :
            log.err('Unsupported WebSocket API state {0}.'.format( self.factory.state))
    
    def authenticate(self):
        """
        Sends authentication information to WebSocket server.
        """
        request_id = WebSocketDeviceHiveProtocol.request_counter.next()
        auth_request = json.dumps({'action': 'authenticate',
                                   'requestId': request_id,
                                   'deviceId': self.factory.device_delegate.device_id(),
                                   'deviceKey': self.factory.device_delegate.device_key()})    
        self.socket.send_frame(True, WS_OPCODE_TEXT_FRAME, auth_request)
    
    def device_save(self):
        pass
    
    def dataReceived(self, data):
        if self.factory.state.value == ProtocolState.ApiMetadata :
            HTTP11ClientProtocol.dataReceived(self, data)
        else :
            self.socket.dataReceived(data)
    
    def _apimetadata_done(self, response) :
        log.msg('ApiInfo respond: {0}.'.format( response ))
        if response.code == 200 :
            def get_response(resp, factory, connector) :
                log.msg('ApiInfo response {0} has been successfully received.'.format(resp))
                if hasattr(factory, 'on_apiinfo_finished') and callable(factory.on_apiinfo_finished) :
                    factory.on_apiinfo_finished(resp, connector)
            
            def err_response(reason, connector) :
                log.msg('Failed to receive ApiInfo response. Reason: {0}.'.format(reason))
                self.factory.retry(connector)
            
            result_proto = Deferred()
            result_proto.addCallbacks(partial(get_response, factory = self.factory, connector = self.transport.connector), partial(err_response, connector = self.transport.connector))
            response.deliverBody(JsonDataConsumer(result_proto))
        else :
            def get_response_text(reason):
                log.err('ApiInfo call failed. Response: <{0}>. Code <{1}>. Reason: <{2}>.'.format(response, response.code, reason))
            response_defer = Deferred()
            response_defer.addCallbacks(get_response_text, get_response_text)
            response.deliverBody(TextDataConsumer(response_defer))
            self.factory.retry(self.transport.connector)
    
    def _critical_error(self, reason) :
        log.err("Device-hive websocket api failure. Critical error: <{0}>".format(reason))
        if reactor.running :
            if hasattr(self.factory, 'on_failure') and callable(self.factory.on_failure) :
                self.factory.on_failure()


class WebSocketDeviceHiveFactory(BaseHTTP11ClientFactory):
    def __init__(self, device_delegate, retries = 3):
        BaseHTTP11ClientFactory.__init__(self, StateHolder(ProtocolState.Unknown), retries)
        self.uri = 'localhost'
        self.host = 'localhost'
        self.port = 80
        self.device_delegate = device_delegate
        self.device_delegate.factory = self
        self.server_timestamp = None
        self.protocol = None
    
    def doStart(self):
        if self.state.value == ProtocolState.Unknown :
            self.state = StateHolder(ProtocolState.ApiMetadata)
        BaseHTTP11ClientFactory.doStart(self)
    
    def buildProtocol(self, addr):
        self.protocol = WebSocketDeviceHiveProtocol(self)
        return self.protocol
    
    def handleConnectionLost(self, connector) :
        if self.state.value == ProtocolState.Register :
            log.msg('Connecting to WebSocket server {0}:{1}.'.format(self.host, self.port))
            reactor.connectTCP(self.host, self.port, self)
        else :
            log.msg('Quiting WebSocket factory.')
    
    def notify(self, notification, kwargs):
        if self.protocol is not None :
            raise NotImplementedError()
        else :
            raise NotImplementedError()
    
    def on_apiinfo_finished(self, response, connector) :
        self.uri, self.host, self.port = parse_url(response['webSocketServerUrl'])
        log.msg('WebSocket service location: {0}, Host: {1}, Port: {2}.'.format(self.uri, self.host, self.port))
        self.uri = response['webSocketServerUrl']
        self.server_timestamp = parse_date(response['serverTimestamp'])
        self.state = StateHolder(ProtocolState.Register)
    
    def on_registration_finished(self, reason=None):
        log.msg('Registration finished. Reason: {0}.'.format(reason))
    
    def on_failure(self):
        log.msg('On failure')

