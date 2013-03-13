# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

"""
Device API implementation for WebSocket protocol
"""

from zope.interface import implements
from twisted.python import log
from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory
from twisted.internet.defer import Deferred, fail
from devicehive import CommandResult, DhError, BaseCommand
from devicehive.interfaces import IProtoFactory, IProtoHandler, IDeviceInfo, INetwork, IDeviceClass, ICommand
from devicehive.ws import IWebSocketProtocolCallback, IWebSocketMessanger, WebSocketError, WebSocketDeviceHiveProtocol


__all__ = ['WsCommand', 'WebSocketFactory']


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


WS_STATE_UNKNOWN          = 0
WS_STATE_WS_CONNECTING    = 1
WS_STATE_WS_CONNECTED     = 2
WS_STATE_WS_DISCONNECTING = 3


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
    
    def send_message(self, message):
        if self.state != WS_STATE_WS_CONNECTED :
            return fail(WebSocketError('protocol is not in WS_STATE_WS_CONNECTED'))
        if self.test_proto() :
            return self.proto.send_message(message)
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
        if ('action' in message) and (message['action'] == 'command/insert') :
            if not 'deviceGuid' in message :
                log.err('Malformed command/insert message {0}.'.format(message))
            else :
                device_id = str(message['deviceGuid']).lower() if ('deviceGuid' in message) and (message['deviceGuid'] is not None) else None
                if device_id in self.devices :
                    self.on_command_insert(WsCommand.create(message), self.devices[device_id])
                else :
                    log.err('Unable to process command {0}. Device {1} is not registered.'.format(message, device_id))
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

