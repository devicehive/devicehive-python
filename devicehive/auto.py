# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

from zope.interface import implements
from twisted.python import log
from twisted.web.client import HTTP11ClientProtocol
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.protocol import ClientFactory, Protocol
from devicehive import ApiInfoRequest
from devicehive.interfaces import IProtoFactory, IProtoHandler
from devicehive.utils import TextDataConsumer, JsonDataConsumer, parse_url, parse_date
from devicehive.device.ws import WebSocketFactory
from devicehive.poll import PollFactory


__all__ = ['AutoProtocol', 'AutoFactory']


class AutoProtocol(HTTP11ClientProtocol):
    """
    The protocol makes API-INFO request. Not intended to external use.
    """
    
    def __init__(self, factory):
        self.factory = factory
    
    def connectionMade(self) :
        self.request(ApiInfoRequest(self.factory.url, self.factory.host)).addCallbacks(self.api_received, self.api_failed)
    
    def api_received(self, response):
        if response.code == 200 :
            result_proto = Deferred()
            result_proto.addCallbacks(self.api_succeed, self.api_failed)
            response.deliverBody(JsonDataConsumer(result_proto))
        else :
            def get_response_text(reason):
                self.api_failed(reason)
            response_defer = Deferred()
            response_defer.addBoth(get_response_text)
            response.deliverBody(TextDataConsumer(response_defer))
    
    def api_succeed(self, resp):
        self.factory.api_received(resp['webSocketServerUrl'], resp['serverTimestamp'])
    
    def api_failed(self, reason):
        self.factory.api_failed(reason)


class AutoFactory(ClientFactory):
    """
    The first thing the factory does, it makes an '/info' request. Then an information
    retrived from response is used to deceide which DeviceHive protocol is more appropriate.
    """
    
    implements(IProtoFactory, IProtoHandler)
    
    url = 'http://localhost'
    host = 'localhost'
    port = 80
    
    ws_url = 'http://localhost'
    ws_host = 'localhost'
    ws_port = 8020
    
    handler = None
    
    def __init__(self, handler):
        if not IProtoHandler.implementedBy(handler.__class__) :
            raise TypeError('The protocol handler has to conform to IProtoHandler interface.')
        self.handler  = handler
        self.handler.factory = self
        self.factory  = None
    
    def buildProtocol(self, addr):
        return AutoProtocol(self)
    
    def clientConnectionFailed(self, connector, reason):
        log.err('Failed to make "/info" call. Reason: {0}.'.format(reason))
        self.handle_connection_failure(reason)
    
    def api_received(self, wsurl, server_time):
        log.msg('The call to "/info" api has finished successfully.')
        try :
            self.server_time = parse_date(server_time)
        except ValueError :
            log.msg('Failed to parse a date-time string "{0}" returned from "/info" api call.'.format(server_time))
            self.server_time = datetime.utcnow()
        if wsurl is not None :
            wsurl = wsurl.strip().replace('ws://', 'http://', 1).replace('wss://', 'https://', 1)
            if wsurl.startswith('http://') or wsurl.startswith('https://') :
                self.ws_url, self.ws_host, self.ws_port = parse_url(wsurl)
                self.handler.on_apimeta(wsurl, self.server_time)
                self.connect_ws()
                return
        self.handler.on_apimeta(wsurl, self.server_time)
        self.connect_poll()
    
    def api_failed(self, reason):
        log.err('The call to "/info" api failed. Reason: {0}.'.format(reason))
        self.on_failure(None, reason)
    
    def handle_connection_failure(self, reason):
        if isinstance(self.factory, WebSocketFactory) :
            self.connect_poll()
        else :
            self.handler.on_connection_failed(reason)
    
    def connect_ws(self):
        log.msg('WebSocket protocol has been selected. URL: {0}; HOST: {1}; PORT: {2};'.format(self.ws_url, self.ws_host, self.ws_port))
        factory = WebSocketFactory(self)
        factory.url  = self.ws_url
        factory.host = self.ws_host
        factory.port = self.ws_port
        factory.timestamp = self.server_time
        reactor.connectTCP(factory.host, factory.port, factory)
    
    def connect_poll(self):
        log.msg('Long-Polling protocol has been selected.')
        factory = PollFactory(self)
        factory.timestamp = self.server_time
        factory.connect(self.url)
    
    # begin IProtoHandler implementation
    def on_apimeta(self, websocket_server, server_time):
        self.handler.on_apimeta(websocket_server, server_time)
    
    def on_connected(self):
        self.handler.on_connected()
    
    def on_connection_failed(self, reason):
        log.err('Sub-factory connection failure. Reason: {0}.'.format(reason))
        self.handle_connection_failure(reason)
    
    def on_closing_connection(self):
        self.handler.on_closing_connection()
    
    def on_command(self, device_id, command, finished):
        self.handler.on_command(device_id, command, finished)
    
    def on_failure(self, device_id, reason):
        self.handler.on_failure(device_id, reason)
    # end IProtoHandler implementation
    
    # begin IProtoFactory implementation
    def authenticate(self, device_id, device_key):
        return self.subfactory(device_id, device_key)
    
    def notify(self, notification, params, device_id = None, device_key = None):
        return self.factory.notify(notification, params, device_id, device_key)
    
    def subscribe(self, device_id = None, device_key = None):
        return self.factory.subscribe(device_id, device_key)
    
    def unsubscribe(self, device_id = None, device_key = None):
        return self.factory.unsubscribe(device_id, device_key)
    
    def device_save(self, info):
        return self.factory.device_save(info)
    
    def connect(self, url):
        reactor.connectDeviceHive(url, self)
    # end IProtoFactory implementation

