# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

"""
Client API implementation for WebSocket protocol.
"""

from sys import maxint
from urlparse import urlparse, urljoin

from twisted.python import log
from twisted.internet import reactor
from twisted.internet.defer import Deferred, fail
from twisted.internet.protocol import ClientFactory, Protocol
from zope.interface import implements

from devicehive import DhError, Notification, BaseCommand
from devicehive.ws import IWebSocketCallback, IWebSocketProtocolCallback, WebSocketDeviceHiveProtocol
from devicehive.interfaces import IClientTransport, IClientApp


def LOG_MSG(msg):
    log.msg(msg)


def LOG_ERR(msg):
    log.err(msg)


class WsCommand(BaseCommand):
    """
    Client implementation of ICommand interface.
    TODO: we need to split it into a command class which is sent to
    device and a command class which is received. Also we need to do it on
    API level. Because there it does not make sense to
    send 'result' field from the client to a device.
    """
    
    def __init__(self, command, parameters=None):
        super(WsCommand, self).__init__()
        self.command = command
        self.parameters = parameters
    
    @staticmethod
    def create(cmd):
        """
        :param cmd:a ``dict`` which is used to construct an instance of WsCommand
        """
        if not isinstance(cmd, dict):
            raise TypeError('cmd argument should be a dict')

        res = WsCommand(cmd['command'], cmd['parameters'] if 'parameters' in cmd else [])

        res.id = cmd['id']
        res.timestamp = cmd['timestamp'] if 'timestamp' in cmd else None
        res.user_id = cmd['userId'] if 'userId' in cmd else None
        res.lifetime = cmd['lifetime'] if 'lifetime' in cmd else None
        res.flags = cmd['flags'] if 'flags' in cmd else None
        res.status = cmd['status'] if 'status' in cmd else None
        res.result = cmd['result'] if 'result' in cmd else None
        return res
    
    def to_dict(self):
        res = {'command': self.command}
        if self.parameters is not None :
            res['parameters'] = self.parameters
        if self.lifetime is not None :
            res['lifetime'] = self.lifetime
        if self.flags is not None :
            res['flags'] = self.flags
        return res


class WebSocketFactory(ClientFactory):
    """
    Implements client factory over websocket protocol.
    See devicehive.interfaces.IClientTransport for methods description.
    """

    implements(IClientTransport, IWebSocketProtocolCallback)

    url = 'ws://localhost'
    proto = None

    def __init__(self, handler):
        if not IClientApp.implementedBy(handler.__class__) :
            raise TypeError('handler must implement devicehive.interfaces.IClientApp interface.')
        self.handler = handler
        self.handler.factory = self
        self.command_callbacks = {}

    def get_client_url(self):
        if not self.url:
            return '/client'
        else:
            path = urlparse(self.url).path
            if path[-1:] != '/':
                path += '/'
            return urljoin(path, 'client')

    def buildProtocol(self, addr):
        self.proto = WebSocketDeviceHiveProtocol(self, self.get_client_url())
        return self.proto

    def clientConnectionFailed(self, connector, reason):
        LOG_ERR('Client connection failed. Reason: {0}.'.format(reason))
        self.handler.failure(reason)
    
    def clientConnectionLost(self, connector, reason):
        pass
    
    # IClientTransport interface implementation
    def authenticate(self, login, password):
        LOG_MSG('Authenticating the client library.')
        defer = Deferred()
        def on_ok(res):
            if res.get('status', 'error') == 'success' :
                LOG_MSG('Client library has been authenticated.')
                defer.callback(res)
            else :
                LOG_ERR('Client failed authenticate. Reason: {0}.'.format(res.get('error', 'unknown')))
                defer.errback(res)
        def on_err(reason):
            LOG_ERR('Failed to send authentication message. Reason: {0}.'.format(reason))
            defer.errback(reason)
        self.proto.send_message({'action': 'authenticate', 'requestId': None, 'login': login, 'password': password}).addCallbacks(on_ok, on_err)
        return defer
    
    def subscribe(self, device_ids):
        if not (isinstance(device_ids, list) or isinstance(device_ids, tuple)) :
            raise TypeError('device_ids should be a list or a tuple')
        LOG_MSG('About to subscribe to notifications for {0} devices.'.format(device_ids))
        defer = Deferred()
        def on_ok(res):
            if res.get('status', 'error') == 'success' :
                LOG_MSG('Subscribed.')
                defer.callback(res)
            else :
                LOG_ERR('Failed to subscribe to device(s) notifications. Reason: {0}.'.format(res.get('error', 'unknown')))
                defer.errback(res)
        def on_err(reason):
            LOG_ERR('Failed to send subscribe command. Reason: {0}.'.format(reason))
            defer.errback(reason)
        return self.proto.send_message({'action': 'notification/subscribe', 'requestId': None, 'deviceGuids': device_ids}).addCallbacks(on_ok, on_err)
    
    def unsubscribe(self, device_ids):
        if not (isinstance(device_ids, list) or isinstance(device_ids, tuple)) :
            raise TypeError('device_ids should be a list or a tuple')
        LOG_MSG('Unsubscibing from devices {0}.'.format(device_ids))
        defer = Deferred()
        def on_ok(res):
            if res.get('status', 'error') == 'success' :
                LOG_MSG('Unsubscribed from device(s) notifications.')
                defer.callback(res)
            else :
                LOG_ERR('Failed to unsubscribe from device(s) notifications. Reason: {0}.'.format(res.get('error', 'unknown')))
                defer.errback(res)
        def on_err(reason):
            LOG_ERR('Failed to send unsubscribe command. Reason: {0}.'.format(reason))
            defer.errback(reason)
        self.proto.send_message({'action': 'notification/unsubscribe',
                           'requestId': None,
                           'deviceGuids': device_ids}).addCallbacks(on_ok, on_err)
        return defer
    
    def command(self, device_id, cmd):
        if not (isinstance(device_id, str) or isinstance(device_id, unicode)) :
            raise TypeError('device_id should be a str or a unicode value')
        
        defer = Deferred()
        def on_ok(res):
            if res.get('status', 'error') == 'success' :
                LOG_MSG('Command successfully sent.')
                cmdid = res['command']['id']
                self.command_callbacks[cmdid] = defer
            else :
                LOG_ERR('Failed to send command {0}. Reason: {1}.'.format(cmd, res.get('error', 'unknown')))
                defer.errback(res)
        def on_err(reason):
            LOG_ERR('Failed to send command {0}. Reason: {1}.'.format(cmd, reason))
            defer.errback(reason)
        self.proto.send_message({'action': 'command/insert',
                                  'requestId': None,
                                  'deviceGuid': device_id,
                                  'command': cmd.to_dict()}).addCallbacks(on_ok, on_err)
        return defer
    
    def do_notification(self, msg):
        LOG_MSG('Notification {0} has been received.'.format(msg['notification']))
        self.handler.do_notification(msg['deviceGuid'], Notification(name = msg['notification']['notification'], parameters = msg['notification']['parameters']))
    
    def do_command_update(self, msg):
        if not isinstance(msg, dict) :
            raise TypeError('msg should be dict')
        cmd = msg.get('command', None)
        if cmd is not None :
            cmdid = cmd.get('id', None)
            if cmdid in self.command_callbacks :
                LOG_MSG('Command {0} update has been received.'.format(msg))
                defer = self.command_callbacks.pop(cmdid)
                ocmd = WsCommand.create(cmd)
                if (isinstance(ocmd.status, str) or isinstance(ocmd.status, unicode)) and ocmd.status.lower() == 'success' :
                    defer.callback(ocmd)
                else :
                    defer.errback(ocmd)
            else :
                LOG_ERR('Unattached command/update message {0} has been received.'.format(msg))
        else :
            LOG_ERR('Malformed command response {0} has been received.'.format(msg))
    
    def ping(self):
        return self.proto.ping()
    
    def connect(self, url):
        LOG_MSG('Connecting to {0} server.'.format(url))
        self.url = url
        reactor.connectDeviceHive(url, self)
    # end IClientTransport interface implementation
    
    # IWebSocketProtocolCallback interface implementation
    def failure(self, reason, connector):
        LOG_ERR('WebSocekt client failure. Reason: {0}.'.format(reason))
        self.handler.failure(reason)
    
    def connected(self):
        LOG_MSG('Client has connected to websocket server.')
        self.handler.connected()
    
    def closing_connection(self):
        LOG_MSG('WebSocket server has requested connection closing.')
        self.handler.closing_connection()
    
    def frame_received(self, message):
        action = message.get('action', '')
        if action == 'command/update' :
            self.do_command_update(message)
        elif action == 'notification/insert' :
            self.do_notification(message)
    # end of IWebSocketProtocolCallback interface implementation

