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
from sys import maxint
from zope.interface import implements, Interface, Attribute
from twisted.python import log
from twisted.python.constants import Values, ValueConstant
from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory, Protocol
from twisted.internet.defer import Deferred, fail
from twisted.web.iweb import IBodyProducer
from twisted.web.client import HTTP11ClientProtocol, Request
from twisted.web.http_headers import Headers
from twisted.protocols.basic import LineReceiver
from urlparse import urlsplit, urljoin
from utils import parse_url, parse_date
from interfaces import IProtoFactory, IProtoHandler


__all__ = ['WebSocketError', 'IWebSocketParserCallback', 'WebSocketParser', 'IWebSocketCallback', 'WebSocketProtocol13',
           'IWebSocketProtocolCallback', 'IWebSocketMessanger', 'WebSocketDeviceHiveProtocol', 'WebSocketDeviceHiveFactory']


class WebSocketError(Exception):
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


class WebSocketProtocol13(object):
    implements(IWebSocketParserCallback)
    
    def __init__(self, handler, transport, host):
        """
        @type handler: C{object}
        @param handler: has to implement C{IWebSocketCallback} interface
        
        @type host: C{str}
        @param host: host string which will be used to form HTTP request header
        """
        self.handler = handler
        self.transport = transport
        self.host = host
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
    
    def test_handler(self):
        return IWebSocketCallback.implementedBy(self.handler.__class__)
    
    def headers_received(self):
        if self.test_handler() :
            self.handler.headers_received()
    
    def frame_received(self, opcode, payload):
        if opcode == WS_OPCODE_PING :
            self.send_frame(1, WS_OPCODE_PONG, payload)
        elif opcode == WS_OPCODE_CONNECTION_CLOSE :
            if self.test_handler() :
                self.handler.closing_connection()
        elif opcode == WS_OPCODE_BINARY_FRAME or opcode == WS_OPCODE_TEXT_FRAME :
            if self.test_handler() :
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
                  'Upgrade: websocket\r\n' + \
                  'Connection: Upgrade\r\n' + \
                  'Sec-WebSocket-Key: {1}' + \
                  'Origin: http://{0}\r\n' + \
                  'Sec-WebSocket-Protocol: device-hive, devicehive\r\n' + \
                  'Sec-WebSocket-Version: 13\r\n\r\n'
        return header.format(self.host, self.security_key).encode('utf-8')
    
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


WS_STATE_UNKNOWN          = 0
WS_STATE_APIMETA          = 1
WS_STATE_WS_CONNECTING    = 2
WS_STATE_WS_CONNECTED     = 3
WS_STATE_WS_DISCONNECTING = 4


class IWebSocketProtocolCallback(Interface):
    state = Attribute('Stores protocol state')
    
    def failure(self, reason, connector):
        """
        Callback signals about critial error
        """
    
    def api_received(self, url, host, port, server_time, connector):
        """
        Callback is called after api matedata has been received
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
        Sends text message
        """


class EmptyDataProducer(object):
    implements(IBodyProducer)
    
    def __init__(self):
        self.length = 0
    
    def startProducing(self, consumer):
        return succeed(True)
    
    def stopProducing(self):
        pass


class ApiMetadataRequest(Request):
    def __init__(self, host):
        super(ApiMetadataRequest, self).__init__('GET', 'info', ApiMetadataRequest.headers(host), EmptyDataProducer())
    
    @staticmethod
    def headers(host) :
        return Headers({'Host': [host], 'Content-Type': ['application/json'], 'Accept': ['application/json']})


class WebSocketDeviceHiveProtocol(HTTP11ClientProtocol):
    
    implements(IWebSocketCallback, IWebSocketMessanger)
    
    def __init__(self, factory):
        HTTP11ClientProtocol.__init__(self)
        self.factory = factory
        self.socket = None
    
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
        if self.test_factory() :
            message = json.loads(payload)
            self.factory.frame_received(message)
    # end IWebSocketCallback
    
    def connectionMade(self):
        if self.test_factory() :
            if self.factory.state == WS_STATE_APIMETA :
                self.request(ApiMetadataRequest(self.factory.host)).addCallbacks(self.api_meta_done, self.critical_error)
            elif self.factory.state == WS_STATE_WS_CONNECTING :
                self.socket = WebSocketProtocol13(self, self.transport, self.factory.host)
                self.socket.send_headers()
        else :
            raise WebSocketError('factory expected')
    
    def dataReceived(self, data):
        if self.test_factory() :
            if self.factory.state == WS_STATE_APIMETA :
                HTTP11ClientProtocol.dataReceived(self, data)
            elif self.socket is not None :
                self.socket.dataReceived(data)
        else :
            raise WebSocketError('factory expected')
    
    def send_message(self, message):
        if not isinstance(message, dict) :
            raise TypeError('message should be a dict')
        if self.socket is not None :
            self.socket.send_frame(True, WS_OPCODE_TEXT_FRAME, json.dumps(message))
            return True
        else :
            return False    
    
    def api_meta_done(self, response):
        if response.code == 200 :
            def get_response(resp, factory, connector):
                url, host, port = parse_url(response['webSocketServerUrl'])
                server_time = parse_date(response['serverTimestamp'])
                factory.api_received(url, host, port, server_time, connector)
            
            def err_response(reason, connector):
                factory.failure(reason, connector)
            
            if self.test_factory() :
                callback = partial(get_response, factory = self.factory, connector = self.transport.connector)
                errback = partial(err_response, connector = self.transport.connector)
                result_proto = Deferred()
                result_proto.addCallbacks(callback, errback)
                response.deliverBody(JsonDataConsumer(result_proto))
        else :
            def get_response_text(reason, connector):
                factory.failure(reason, connector)
            
            callback = partial(get_response_text, connector = self.transport.connector)
            response_defer = Deferred()
            response_defer.addCallbacks(callback, callback)
            response.deliverBody(TextDataConsumer(response_defer))
    
    def critical_error(self, reason):
        if self.test_factory() :
            self.factory.failure(reason, self.transport.connector)


class WebSocketDeviceHiveFactory(ClientFactory):
    implements(IWebSocketProtocolCallback, IProtoFactory)
    
    uri = 'localhost'
    host = 'localhost'
    port = 80
    proto = None
    handler = None
    callbacks = dict()
    state = WS_STATE_UNKNOWN
    
    def __init__(self, handler):
        """
        @type handler: C{object}
        @param handler: handler has to implement C{IProtoHandler} interface
        """
        ClientFactory.__init__(self)
        self.handler = handler
        if self.test_handler() :
            self.handler.factory = self
        else :
            raise TypeError('handler should implements IProtoHandler interface')
    
    def test_handler(self):
        return IProtoHandler.implementedBy(self.handler.__class__)
    
    def test_proto(self):
        return IWebSocketMessanger.implementedBy(self.proto.__class__)
    
    def doStart(self):
        if self.state == WS_STATE_UNKNOWN :
            self.state = WS_STATE_APIMETA
        ClientFactory.doStart(self)
    
    def buildProtocol(self, addr):
        self.proto = WebSocketDeviceHiveProtocol(self)
        return self.proto
    
    def handleConnectionLost(self, connector) :
        if self.state == WS_STATE_WS_CONNECTING :
            reactor.connectTCP(self.host, self.port, self)
    
    def request_counter():
        request_number = 1
        while True :
            yield request_number
            if request_number == maxint :
                request_number = 0
            else :
                request_number += 1
    request_counter = request_counter()
    
    def send_message(self, message):
        if self.state != WS_STATE_WS_CONNECTED :
            return fail(WebSocketError('protocol is not in WS_STATE_WS_CONNECTED'))
        if self.test_proto() :
            msgid = self.request_counter.next()
            message['requestId'] = msgid
            self.callbacks[msgid] = Deferred()
            if self.proto.send_message(message) :
                return self.callbacks[msgid]
            else :
                err = self.callbacks[msgid]
                del self.callbacks[msgid]
                err.fail(WebSocketError('failed to send websocket frame'))
                return err
        else :
            return fail(WebSocketError('protocol is not set'))
    
    # begin IWebSocketProtocolCallback implementation
    def failure(self, reason, connector):
        log.err('Critial error. Reason: {0}.'.format(reason))
    
    def api_received(self, url, host, port, server_time, connector):
        self.uri = url
        self.host = host
        self.port = port
        self.server_time = server_time
        self.state = WS_STATE_WS_CONNECTING
        if self.test_handler() :
            self.handler.on_apimeta(url, server_time)
    
    def connected(self):
        self.state = WS_STATE_WS_CONNECTED
        if self.test_handler() :
            self.handler.on_connected()
    
    def closing_connection(self):
        self.state = WS_STATE_WS_DISCONNECTING
        if self.test_handler() :
            self.handler.on_closing_connection()
    
    def frame_received(self, message):
        if ('requestId' in message) and (message['requestId'] in self.callbacks) :
            reqid = message['requestId']
            deferred = self.callbacks[reqid]
            del self.callbacks[reqid]
            d.callback(message)
        elif ('action' in message) and (message['action'] == 'command/insert') :
            if self.test_handler() :
                cmd = message['command']
                def on_ok(result):
                    raise NotImplementedError()
                    self.update_command(self, cmd, (cmd['deviceId'] if 'deviceId' in cmd else None), (cmd['deviceKey'] if 'deviceKey' is cmd else None))
                def on_err(reason):
                    raise NotImplementedError()
                    self.update_command(self, cmd, (cmd['deviceId'] if 'deviceId' in cmd else None), (cmd['deviceKey'] if 'deviceKey' is cmd else None))
                finished = Deferred()
                finished.addCallbacks(on_ok, on_err)
                self.handler.on_command(message['deviceGuid'], message['command'], finished)
            else :
                raise WebSocketError('handler should be set')
    # end IWebSocketProtocolCallback    
    
    # begin IProtoFactory implementation
    def authenticate(self, device_id, device_key):
        request = {'action': 'authenticate',
                   'deviceId': device_id,
                   'deviceKey': device_key}
        return self.send_message(request)
    
    def notify(self, notification, device_id = None, device_key = None):
        request = {'action': 'notification/insert', 'notification': {'notification': notification, 'parameters': params}}
        if (device_id is not None) or (device_key is not None) :
            request['deviceId'] = device_id
            request['deviceKey'] = device_key
        return self.send_message(request)
    
    def update_command(self, command, device_id = None, device_key = None):
        # TODO: strict type for command parameter. It has to implement ICommand interface
        request = {'action': 'command/update',
                   'commandId': command['id'],
                   'command': {'command': command['command'],
                               'parameters': command['parameters'],
                               'lifetime': command['lifetime'],
                               'flags': command['flags'],
                               'status': command['status'],
                               'result': command['result']}}
        if (device_id is not None) or (device_key is not None) :
            request['deviceId'] = device_id
            request['deviceKey'] = device_key
        return self.send_message(request)
    
    def subscribe(self, device_id = None, device_key = None):
        request = {'action': 'command/subscribe'}
        if (device_id is not None) or (device_key is not None) :
            request['device_id'] = device_id
            request['device_key'] = device_key
        return self.send_message(request)
    
    def unsubscribe(self, device_id = None, device_key = None):
        request = {'action': 'command/unsubscribe'}
        if (device_id is not None) or (device_key is not None) :
            request['deviceId'] = device_id
            request['deviceKey'] = device_key
        return self.send_message(request)
    
    def device_save(self, info):
        if not IDeviceInfo.implementedBy(device_info.__class__) :
            raise WebSocketError('device_info has to implement IDeviceInfo interface')
        request = {'action': 'device/save',
                   'deviceId': info.id,
                   'deviceKey': info.key,
                   'device': {'key': info.key,
                              'name': info.name,
                              'status': info.status,
                              'network': info.network.to_dict() if INetwork.implementedBy(info.network.__class__) else info.network,
                              'deviceClass': info.device_class.to_dict() if IDeviceClass.implementedBy(info.device_class.__class__) else info.device_class,
                              'equipment': [e.to_dict() for e in info.equipment]}}
        return self.send_message(request)
    # end IProtoFactory implementation

