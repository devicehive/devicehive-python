# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

"""
Common websocket facilities.
"""

import json
import base64
import sha
import struct
import urlparse
from time import time
from random import Random
from array import array
from sys import maxint
from zope.interface import implements, Interface, Attribute
from twisted.python import log
from twisted.python.constants import Values, ValueConstant
from twisted.internet import reactor
from twisted.internet.defer import Deferred, fail
from twisted.internet.protocol import Protocol
from twisted.protocols.basic import LineReceiver
from devicehive import DhError


__all__ = ['WebSocketError', 'WebSocketState', 'WebSocketParser', 'WebSocketProtocol13',
           'WebSocketDeviceHiveProtocol', 'IWebSocketParserCallback',
           'IWebSocketProtocolCallback', 'IWebSocketMessanger', 'IWebSocketCallback']


class WebSocketError(DhError):
    def __init__(self, msg = '') :
        super(WebSocketError, self).__init__('WebSocket error. Reason: {0}.'.format(msg))


class IWebSocketParserCallback(Interface) :
    def status_received(self, proto_version, code, status) :
        """
        Called when status line is received
        
        @param proto_version - protocol version, i.e. HTTP/1.1
        @param code - HTTP response code
        @param status - HTTP respose status message
        """
    
    def header_received(self, name, value):
        """
        Passes received header
        
        @param name - header name
        @param value - header value
        """
    
    def headers_received(self) :
        """
        Method is called after all heades have been received. Also this
        means that connection has been established.
        """
    
    def frame_received(self, opcode, payload):
        """
        Method passes opcode and payload of newly received websocket frame
        """


class IWebSocketProtocolCallback(Interface):
    def failure(self, reason, connector):
        """
        Callback signals about critial error
        """
    
    def connected(self):
        """
        Callback is called after websocket connection has been established.
        """
    
    def closing_connection(self):
        """
        Callback is called in response to connection_close websocket frame.
        """
    
    def frame_received(self, message):
        """
        Callback is called when a new text or binary websocket frame is received.
        """


class IWebSocketMessanger(Interface):
    def send_message(self, message):
        """
        Sends text message to a server.
        """
    
    def ping(self):
        """
        Sends a ping request to a server.
        """


class IWebSocketCallback(Interface):
    def headers_received(self):
        """
        Called when all headers have been received
        """
    
    def closing_connection(self):
        """
        Called when server going to close connection
        """
    
    def frame_received(self, payload):
        """
        Called when a new text or binary frame has been received
        """


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
        # attributes which store frame data and parameters
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
    
    def test_handler(self):
        return IWebSocketParserCallback.implementedBy(self.handler.__class__)
    
    def status_received(self, line) :
        if self.test_handler() :
            proto_version, code, status = line.split(' ', 2)
            self.handler.status_received(proto_version, int(code, 10), status)
    
    def header_received(self, name, value):
        if self.test_handler() :
            self.handler.header_received(name, value)
    
    def headers_received(self) :
        if self.test_handler() :
            self.handler.headers_received()
        self.state = WebSocketState.WsHeader
        self.setRawMode()
    
    def frame_received(self, opcode, payload):
        if self.test_handler() :
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
    implements(IWebSocketParserCallback)
    
    def __init__(self, handler, transport, host, uri):
        """
        @type handler: C{object}
        @param handler: has to implement C{IWebSocketCallback} interface
        
        @type host: C{str}
        @param host: host string which will be used to form HTTP request header
        
        @type uri: C{str}
        @param uri: device uri
        """
        self.handler = handler
        self.transport = transport
        self.host = host
        self.uri = uri
        self.rand = Random(long(time()))
        self.security_key = base64.b64encode(array('B', [self.rand.randint(0, 0xff) for x in range(12)]).tostring())
        self.parser = WebSocketParser(self)
    
    def dataReceived(self, data):
        self.parser.dataReceived(data)
    
    def status_received(self, proto_version, code, status):
        if proto_version != 'HTTP/1.1' :
            raise WebSocketError('unsupported protocol {0}'.format(proto_version))
        if code != 101 :
            raise WebSocketError('websocket server rejected protocol upgrade with code {0} and status {1}.'.format(code, status))
    
    def header_received(self, name, value):
        loname = name.lower()
        if loname == 'sec-websocket-accept' :
            if not self.validate_security_answer(value) :
                raise WebSocketError('websocket server returned invalid security key {0} in response to {1}'.format(value, self.security_key))
            pass
        elif loname == 'connection' :
            if value.lower() != 'upgrade' :
                raise WebSocketError('websocket server failed to upgrade connection, status = {0}'.format(value))
        elif loname == 'upgrade' :
            if value.lower() != 'websocket' :
                raise WebSocketError('websocket server upgraded protocol to invalid state {0}'.format(value))
    
    def test_handler(self):
        return IWebSocketCallback.implementedBy(self.handler.__class__)
    
    def headers_received(self):
        if self.test_handler() :
            self.handler.headers_received()
    
    def frame_received(self, opcode, payload):
        log.msg('Websocket frame ({0}) has been received. Frame data: {1}.'.format(opcode, payload))
        if opcode == WS_OPCODE_PING:
            log.msg('Responding with pong packaet.')
            self.send_frame(True, WS_OPCODE_PONG, payload)
        elif opcode == WS_OPCODE_PONG:
            self.handler.pong_received(payload)
        elif opcode == WS_OPCODE_CONNECTION_CLOSE :
            if self.test_handler():
                self.handler.closing_connection()
        elif opcode == WS_OPCODE_BINARY_FRAME or opcode == WS_OPCODE_TEXT_FRAME :
            if self.test_handler():
                self.handler.frame_received(payload)
        else:
            raise WebSocketError('opcode {0} is not supported'.format(opcode))
    
    def validate_security_answer(self, answer):
        skey = sha.new(self.security_key + WS_GUID.encode('utf-8'))
        key = base64.b64encode(skey.digest())
        return answer == key
    
    def send_headers(self) :
        header = 'GET {0} HTTP/1.1\r\n'.format(self.uri) + \
                  'Host: {0}\r\n' + \
                  'Upgrade: websocket\r\n' + \
                  'Connection: Upgrade\r\n' + \
                  'Sec-WebSocket-Key: {1}\r\n' + \
                  'Origin: http://{0}\r\n' + \
                  'Sec-WebSocket-Protocol: device-hive, devicehive\r\n' + \
                  'Sec-WebSocket-Version: 13\r\n\r\n'
        data = header.format(self.host, self.security_key).encode('utf-8')
        log.msg('Sending header: {0}'.format(data))
        self.transport.write(data)
    
    def send_frame(self, fin, opcode, data) :
        prefix = (0x80 if fin else 0x00) | opcode
        frame = struct.pack('B', prefix )[0]
        l = len(data)
        if l < 126:
            frame += struct.pack('B', l | 0x80)[0]
        elif l <= 0xFFFF:
            frame += struct.pack('!BH', 126 | 0x80, l)
        else:
            frame += struct.pack('!BQ', 127 | 0x80, l)
        mask  = chr(self.rand.randint(0, 0xff)) + chr(self.rand.randint(0, 0xff)) + chr(self.rand.randint(0, 0xff)) + chr(self.rand.randint(0, 0xff))
        frame += mask
        frame += array('B', [ord(data[i]) ^ ord(mask[i % 4]) for i in range(len(data))]).tostring()
        self.transport.write(frame)


class WebSocketDeviceHiveProtocol(Protocol):
    
    implements(IWebSocketCallback, IWebSocketMessanger)
    
    def __init__(self, factory, uri, timeout = 10):
        """
        @type uri: C{str}
        @param uri: an uri which is used during handshake
        
        @type timeout: C{int}
        @param timeout: timeout in seconds for requests
        """
        self.factory = factory

        path = urlparse.urlparse(factory.url).path or '/'
        self.uri = urlparse.urljoin(path, uri)
        self.socket = None
        self.timeout = timeout

        # Each devicehive message has an associated response.
        self.msg_callbacks = {}
        self.ping_callbacks = {}
    
    def test_factory(self):
        return IWebSocketProtocolCallback.implementedBy(self.factory.__class__)
    
    # begin IWebSocketCallback
    def headers_received(self):
        if self.test_factory() :
            self.factory.connected()
    
    def closing_connection(self):
        if self.test_factory() :
            self.factory.closing_connection()
    
    def frame_received(self, payload):
        log.msg('Websocket message has been received {0}.'.format(payload))
        message = json.loads(payload)
        if 'requestId' in message :
            request_id = message['requestId']
            if request_id in self.msg_callbacks :
                defer = self.msg_callbacks.pop(request_id)
                defer.callback(message)
        self.factory.frame_received(message)
    
    def pong_received(self, ping_payload):
        if ping_payload in self.ping_callbacks :
            log.msg('Pong {0} received.'.format(ping_payload))
            self.ping_callbacks[ping_payload].callback(ping_payload)
    # end IWebSocketCallback
    
    def connectionMade(self):
        self.socket = WebSocketProtocol13(self, self.transport, self.factory.host, self.uri)
        self.socket.send_headers()
    
    def dataReceived(self, data):
        if self.test_factory() :
            if self.socket is not None :
                self.socket.dataReceived(data)
        else :
            raise WebSocketError('factory expected')
    
    def request_counter():
        """
        Internal method which is used to generate request ids for websocket messages.
        """
        request_number = 1
        while True :
            yield request_number
            if request_number == maxint :
                request_number = 0
            else :
                request_number += 1
    request_counter = request_counter()
    
    def send_message(self, message):
        if not isinstance(message, dict) :
            return fail(TypeError('message should be a dict'))
        
        if self.socket is not None :
            defer = Deferred()
            # generating message id
            msg_id = self.request_counter.next()
            message['requestId'] = msg_id
            self.msg_callbacks[msg_id] = defer
            # all messages should be in utf-8
            data = json.dumps(message).encode('utf-8')
            log.msg('Sending websocket text frame. Payload: {0}'.format(data))
            self.socket.send_frame(True, WS_OPCODE_TEXT_FRAME, data)
            return defer
        else :
            return fail(WebSocketError('Failed to send websocket message. Websocket is not set.'))
    
    def ping_counter():
        ping_number = 1
        while True :
            yield hex(ping_number).encode('utf-8')
            if ping_number == maxint :
                ping_number = 0
            else :
                ping_number += 1
    ping_counter = ping_counter()
    
    def ping(self):
        if self.socket is not None :
            pingid = self.ping_counter.next()
            defer = Deferred()
            self.ping_callbacks[pingid] = defer
            
            log.msg('Ping {0} devicehive server.'.format(pingid))
            self.socket.send_frame(True, WS_OPCODE_PING, pingid)
            
            # I cannot move it into decorator logic because I need a reference to
            # a function which is clousered to a local scope.
            def on_timeout():
                if pingid in self.ping_callbacks :
                    defer = self.ping_callbacks.pop(pingid)
                    defer.errback(WebSocketError('Ping {0} timeout.'.format(pingid)))
            timeout_defer = reactor.callLater(self.timeout, on_timeout)
            def cancel_timeout(result, *args, **kwargs):
                if timeout_defer.active() :
                    log.msg('Cancelling timeout function call for ping {0}.'.format(pingid))
                    timeout_defer.cancel()
                return result
            defer.addBoth(cancel_timeout)
            
            return defer
        else :
            return fail(WebSocketError('Failed to send ping to the server. Websocket is not established.'))

