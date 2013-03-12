# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

import json
import base64
import sha
import struct
from time import time
from random import Random
from array import array
from sys import maxint
from zope.interface import implements, Interface, Attribute
from twisted.python import log
from twisted.python.constants import Values, ValueConstant
from twisted.internet import reactor
from twisted.internet.defer import Deferred, fail
from twisted.internet.protocol import ClientFactory, Protocol
from twisted.protocols.basic import LineReceiver
from devicehive import ApiInfoRequest, CommandResult, DhError, BaseCommand
from devicehive.utils import JsonDataConsumer, parse_url, parse_date
from devicehive.interfaces import IProtoFactory, IProtoHandler, IDeviceInfo, INetwork, IDeviceClass, ICommand


__all__ = ['WebSocketError', 'WebSocketState', 'WebSocketParser', 'WebSocketProtocol13',
           'WebSocketDeviceHiveProtocol', 'WsCommand', 'WebSocketFactory',
           'IWebSocketParserCallback', 'IWebSocketProtocolCallback', 'IWebSocketMessanger', 'IWebSocketCallback']


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


class IWebSocketProtocolCallback(Interface):
    state = Attribute('Stores protocol state')
    
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
        Sends text message
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
            raise WebSocketError('websocket server rejected protocol upgrade with code {0}'.format(code))
    
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
        self.transport.write(header.format(self.host, self.security_key).encode('utf-8'))
    
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


WS_STATE_UNKNOWN          = 0
WS_STATE_WS_CONNECTING    = 1
WS_STATE_WS_CONNECTED     = 2
WS_STATE_WS_DISCONNECTING = 3


class WebSocketDeviceHiveProtocol(Protocol):
    
    implements(IWebSocketCallback, IWebSocketMessanger)
    
    def __init__(self, factory, uri):
        """
        @type uri: C{str}
        @param uri: an uri which is used during handshake
        """
        self.factory = factory
        self.uri = uri
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
            if self.factory.state == WS_STATE_WS_CONNECTING :
                self.socket = WebSocketProtocol13(self, self.transport, self.factory.host, self.uri)
                self.socket.send_headers()
        else :
            raise WebSocketError('factory expected')
    
    def dataReceived(self, data):
        if self.test_factory() :
            if self.socket is not None :
                self.socket.dataReceived(data)
        else :
            raise WebSocketError('factory expected')
    
    def send_message(self, message):
        if not isinstance(message, dict) :
            raise TypeError('message should be a dict')
        if self.socket is not None :
            data = json.dumps(message).encode('utf-8')
            log.msg('Sending websocket text frame. Payload: {0}'.format(data))
            self.socket.send_frame(True, WS_OPCODE_TEXT_FRAME, data)
            return True
        else :
            return False    


class WsCommand(BaseCommand):
    @staticmethod
    def create(message):
        """
        Creates C{ICommand} instance from command/insert message dictionary
        
        @type message: C{dict}
        @param message: command/insert command/insert message
        """
        cmd = message['command']
        
        res = WsCommand()
        res.id = cmd['id']
        res.timestamp = cmd['timestamp'] if 'timestamp' in cmd else None
        res.user_id = cmd['userId'] if 'userId' in cmd else None
        res.command = cmd['command']
        res.parameters = cmd['parameters'] if 'parameters' in cmd else []
        res.lifetime = cmd['lifetime'] if 'lifetime' in cmd else None
        res.flags = cmd['flags'] if 'flags' in cmd else None
        res.status = cmd['status'] if 'status' in cmd else None
        res.result = cmd['result'] if 'result' in cmd else None
        return res
    
    def to_dict(self):
        cmd = {'id': self.id, 'command': self.command, 'parameters': self.parameters}
        if self.timestamp is not None :
            cmd['timestamp'] = self.timestamp
        if self.user_id is not None :
            cmd['userId'] = self.user_id
        if self.lifetime is not None :
            cmd['lifetime'] = self.lifetime
        if self.flags is not None :
            cmd['flags'] = self.flags
        if self.status is not None :
            cmd['status'] = self.status
        if self.result is not None :
            cmd['result'] = self.result
        return cmd


class WebSocketFactory(ClientFactory):
    """
    Implements device factory over websocket protocol.
    """
    
    implements(IWebSocketProtocolCallback, IProtoFactory)
    
    url = 'localhost'
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
        self.handler = handler
        if self.test_handler() :
            self.handler.factory = self
        else :
            raise TypeError('handler should implements IProtoHandler interface')
        self.devices = {}
    
    def test_handler(self):
        return IProtoHandler.implementedBy(self.handler.__class__)
    
    def test_proto(self):
        return IWebSocketMessanger.implementedBy(self.proto.__class__)
    
    def doStart(self):
        if self.state == WS_STATE_UNKNOWN :
            self.state = WS_STATE_WS_CONNECTING
        ClientFactory.doStart(self)
    
    def buildProtocol(self, addr):
        self.proto = WebSocketDeviceHiveProtocol(self, '/device')
        return self.proto
    
    def clientConnectionFailed(self, connector, reason):
        log.err('Failed to connect to {0}, host: {1}, port: {2}. Reason: {3}.'.format(self.url, self.host, self.port, reason))
        if self.test_handler() :
            self.handler.on_connection_failed(reason)
    
    def clientConnectionLost(self, connector, reason):
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
        if self.test_handler():
            self.handler.on_failure(None, reason)
    
    def connected(self):
        self.state = WS_STATE_WS_CONNECTED
        if self.test_handler() :
            self.handler.on_connected()
    
    def closing_connection(self):
        self.state = WS_STATE_WS_DISCONNECTING
        if self.test_handler() :
            self.handler.on_closing_connection()
    
    def frame_received(self, message):
        log.msg('Message received {0}.'.format(message))
        if ('requestId' in message) and (message['requestId'] in self.callbacks) :
            reqid = message['requestId']
            deferred = self.callbacks[reqid]
            del self.callbacks[reqid]
            deferred.callback(message)
        elif ('action' in message) and (message['action'] == 'command/insert') :
            if not 'deviceGuid' in message :
                log.err('Malformed command/insert message {0}.'.format(message))
            else :
                device_id = str(message['deviceGuid']).lower() if ('deviceGuid' in message) and (message['deviceGuid'] is not None) else None
                if device_id in self.devices :
                    self.on_command_insert(WsCommand.create(message), self.devices[device_id])
                else :
                    log.err('Unable to process command {0}. Device {1} is not registered.'.format(message, device_id))
        else :
            raise DhError('unsupported message {0}'.format(message))
    # End of IWebSocketProtocolCallback interface implementation
    
    def on_command_insert(self, cmd, info):
        """
        @type cmd: C{object}
        @param cmd: object which implements C{ICommand}
        
        @type info: C{object}
        @param info: C{IDeviceInfo} object which is receiving the command
        """
        log.msg('Command {0} has been received for device {1}.'.format(cmd, info))
        if self.test_handler() :
            def on_ok(result):
                log.msg('The command "{0}" successfully processed. Result: {1}.'.format(cmd, result))
                if isinstance(result, CommandResult) :
                    cmd.status = result.status
                    cmd.result = result.result
                else :
                    cmd.status = 'Success'
                    cmd.result = result
                self.update_command(cmd, device_id = info.id, device_key = info.key)
            #
            def on_err(reason):
                log.err('Failed to process command "{0}". Reason: {1}.'.format(cmd, reason))
                if isinstance(reason, Exception) :
                    cmd.status = 'Failed'
                    cmd.result = reason.message
                elif hasattr(reason, 'value') :
                    if isinstance(reason.value, CommandResult) :
                        cmd.status = reason.value.status
                        cmd.result = reason.value.result
                    elif isinstance(reason.value, Exception) :
                        cmd.status = 'Failed'
                        cmd.result = reason.value.message
                    else :
                        cmd.status = 'Failed'
                        cmd.result = reason.value
                else :
                    cmd.status = 'Failed'
                    cmd.result = 'Unhandled Exception'
                self.update_command(cmd, device_id = info.id, device_key = info.key)
            #
            finished = Deferred()
            finished.addCallbacks(on_ok, on_err)
            try :
                self.handler.on_command(info.id, cmd, finished)
            except Exception as ex:
                err = DhError('Failed to invoke command {0}. Reason: {1}.'.format(cmd, ex.message))
                log.err(err.message)
                on_err(err)
        else :
            raise WebSocketError('handler should be set')
    
    # begin IProtoFactory implementation
    def authenticate(self, device_id, device_key):
        request = {'action': 'authenticate',
                   'deviceId': device_id,
                   'deviceKey': device_key}
        return self.send_message(request)
    
    def notify(self, notification, params, device_id = None, device_key = None):
        request = {'action': 'notification/insert', 'notification': {'notification': notification, 'parameters': params}}
        if (device_id is not None) :
            request['deviceId'] = device_id
        if (device_key is not None) :
            request['deviceKey'] = device_key
        return self.send_message(request)
    
    def update_command(self, command, device_id = None, device_key = None):
        if not ICommand.implementedBy(command.__class__) :
            raise DhError('{0}.update_command expects ICommand'.format(self.__class__.__name__))
        request = {'action': 'command/update', 'commandId': command.id, 'command': command.to_dict()}
        if device_id is not None :
            request['deviceId'] = device_id
        if device_key is not None :
            request['deviceKey'] = device_key
        return self.send_message(request)
    
    def subscribe(self, device_id = None, device_key = None):
        log.msg('Subscribe device {0}.'.format(device_id))
        request = {'action': 'command/subscribe'}
        if device_id is not None :
            request['deviceId'] = device_id
        if device_key is not None :
            request['deviceKey'] = device_key
        return self.send_message(request)
    
    def unsubscribe(self, device_id = None, device_key = None):
        request = {'action': 'command/unsubscribe'}
        if device_id is not None :
            request['deviceId'] = device_id
        if device_key is not None :
            request['deviceKey'] = device_key
        return self.send_message(request)
    
    def device_save(self, info):
        log.msg('device_save {0}'.format(info))
        if not IDeviceInfo.implementedBy(info.__class__) :
            raise WebSocketError('info parameter has to implement IDeviceInfo interface')
        dev = {'key': info.key, 'name': info.name, 'equipment': [e.to_dict() for e in info.equipment]}
        if info.status is not None :
            dev['status'] = info.status
        if info.network is not None :
            dev['network'] = info.network.to_dict() if INetwork.implementedBy(info.network.__class__) else info.network
        if info.device_class is not None :
            dev['deviceClass'] = info.device_class.to_dict() if IDeviceClass.implementedBy(info.device_class.__class__) else info.device_class
        request = {'action': 'device/save', 'deviceId': info.id, 'deviceKey': info.key, 'device': dev}
        def on_ok(result):
            key = str(info.id).lower()
            self.devices[key] = info
        return self.send_message(request).addCallback(on_ok)
    
    def connect(self, url):
        reactor.connectDeviceHive(url, self)
    # end IProtoFactory implementation

