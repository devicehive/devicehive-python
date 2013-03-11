# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:


from sys import maxint
from twisted.python import log
from twisted.internet import reactor
from twisted.internet.defer import Deferred, fail
from twisted.internet.protocol import ClientFactory, Protocol
from zope.interface import implements

from devicehive import DhError, Notification
from devicehive.ws import IWebSocketCallback, IWebSocketProtocolCallback, WS_STATE_UNKNOWN, WS_STATE_WS_CONNECTING, WebSocketDeviceHiveProtocol, WS_STATE_WS_CONNECTED
from devicehive.interfaces import IClientFactory, IClientApp


def LOG_MSG(msg):
    log.msg(msg)


def LOG_ERR(msg):
    log.err(msg)


class WebSocketClientError(DhError):
    """
    Base error type for this module.
    """
    
    def __init__(self, msg = None):
        super(WebSocketClientError, 'Client websocket failure. Reason: {0}.'.format(msg if msg is not None else 'unknown'))


class WebSocketFactory(ClientFactory):
    """
    Implements client factory over websocket protocol.
    """
    
    implements(IClientFactory, IWebSocketProtocolCallback)
    
    url  = 'localhost'
    host = 'localhost'
    port = 8010
    proto = None
    
    def __init__(self, handler):
        if not IClientApp.implementedBy(handler.__class__) :
            raise TypeError('handler must implement devicehive.interfaces.IClientApp interface.')
        self.handler = handler
        self.handler.factory = self
        self.callbacks = {}
    
    def request_counter():
        """
        Internal method which is used to generate request ids for
        websocket messages.
        """
        request_number = 1
        while True :
            yield request_number
            if request_number == maxint :
                request_number = 0
            else :
                request_number += 1
    request_counter = request_counter()
    
    def doStart(self):
        if self.state == WS_STATE_UNKNOWN :
            self.state = WS_STATE_WS_CONNECTING
        ClientFactory.doStart(self)
    
    def buildProtocol(self, addr):
        self.proto = WebSocketDeviceHiveProtocol(self)
        return self.proto
    
    def clientConnectionFailed(self, connector, reason):
        print 'Connection failed {0}, {1}, {2}'.format(self.url, self.host, self.port)
    
    def clientConnectionLost(self, connector, reason):
        print 'Connection lost'
    
    def send_message(self, message):
        msgid = self.request_counter.next()
        message['requestId'] = msgid
        self.callbacks[msgid] = Deferred()
        
        if self.proto.send_message(message) :
            return self.callbacks[msgid]
        else :
            err = self.callbacks[msgid]
            del self.callbacks[msgid]
            err.fail('failed to send websocket frame')
            return err
    
    # IClientFactory interface implementation
    def authenticate(self, login, password):
        LOG_MSG('About to send authentication request.')
        return self.send_message({'action': 'authenticate', 'requestId': None, 'login': login.encode('utf-8'), 'password': password.encode('utf-8')})
    
    def subscribe(self, device_ids):
        if not (isinstance(device_ids, list) or isinstance(device_ids, tuple)) :
            raise TypeError('device_ids should be a list or a tuple')
        LOG_MSG('About to subscribe to notifications for {0} devices.'.format(device_ids))
        return self.send_message({'action': 'notification/subscribe', 'requestId': None, 'deviceGuids': device_ids})
    
    def unsubscribe(self, device_ids):
        if not (isinstance(device_ids, list) or isinstance(device_ids, tuple)) :
            raise TypeError('device_ids should be a list or a tuple')
        LOG_MSG('Unsubscibing from devices {0}.'.format(device_ids))
        return self.send_message({'action': 'notification/unsubscribe', 'requestId': None, 'deviceGuids': device_ids})
    
    def command(self, device_id, cmd):
        """
        Sends command into device.
        """
        if not (isinstance(device_id, str) or isinstance(device_id, unicode)) :
            raise TypeError('device_id should be a str or a unicode value')
        return self.send_message({'action': 'command/insert',
                                  'deviceGuid': device_id,
                                  'command': cmd.to_dict()})
    
    def do_notification(self, msg):
        LOG_MSG('Notification {0} has been received.'.format(msg['notification']))
        self.handler.do_notification(msg['deviceGuid'], Notification(name = msg['notification']['notification'], parameters = msg['notification']['parameters']))
    # end IClientFactory interface implementation
    
    # IWebSocketProtocolCallback interface implementation
    state = WS_STATE_UNKNOWN
    
    def failure(self, reason, connector):
        LOG_ERR('WebSocekt client failure. Reason: {0}.'.format(reason))
        self.handler.failure(reason)
    
    def connected(self):
        self.handler.connected()
    
    def closing_connection(self):
        self.handler.closing_connection()
    
    def frame_received(self, message):
        LOG_MSG('Message has been received {0}.'.format(message))
        if ('action' in message) and (message['action'] == 'command/update') :
            pass
        if ('action' in message) and (message['action'] == 'notification/insert') :
            self.do_notification(self, message)
        elif ('requestId' in message) and (message['requestId'] in self.callbacks) :
            reqid = message['requestId']
            deferred = self.callbacks[reqid]
            del self.callbacks[reqid]
            deferred.callback(message)
    # end of IWebSocketProtocolCallback interface implementation

