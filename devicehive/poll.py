# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

import json
from datetime import datetime
from zope.interface import implements, Interface, Attribute
from twisted.python import log
from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory
from twisted.internet.defer import Deferred, succeed, fail
from twisted.web.iweb import IBodyProducer
from twisted.web.client import HTTP11ClientProtocol, Request
from twisted.web.http_headers import Headers
from utils import parse_url, parse_date, url_path
from devicehive import DhError, CommandResult, BaseCommand
from devicehive.interfaces import IProtoFactory, IProtoHandler
from devicehive.utils import TextDataConsumer, JsonDataConsumer


__all__ = ['JsonDataProducer', 'JsonDataConsumer', 'BaseRequest', 'RegisterRequest', 'NotifyRequest',
           'ReportRequest', 'CommandRequest', 'PollFactory']


def LOG_MSG(msg):
    log.msg(msg)


def LOG_ERR(msg):
    log.err(msg)


class IPollOwner(Interface):
    url  = Attribute('devicehive API url')
    host = Attribute('devicehive host. it is used dring HTTP headers forming. TODO: consider to get rid of it.')
    port = Attribute('devicehive API port')
    
    def on_command(self, info, cmd, finish):
        """
        Processes devicehive command.
        
        @type info: C{object}
        @param info: Object which implements C{IDeviceInfo} interface. Specifies which device has received command.
        
        @type cmd: C{dict}
        @param cmd: command
        
        @type finish: C{Defer}
        @param finish: a user has to callback this deferred in order to signal to the library that commad has been processed.
        """
    
    def on_failure(self, device_id, reason):
        """
        @type device_id: C{str}
        @param device_id: device guid
        """


class JsonDataProducer(object):
    """
    L{JsonDataProducer}. This class is not intended for external use.
    """
    implements(IBodyProducer)

    def __init__(self, data):
        try:
            self.data = json.dumps(data)
            self.error = None
        except Exception, error:
            self.error = error
        self.length = len(self.data)

    def startProducing(self, consumer):
        if self.error is None:
            try:
                consumer.write(self.data)
                return succeed(None)
            except Exception, error:
                return fail(error)
        else:
            return fail(self.error)

    def stopProducing(self):
        pass

    def pauseProducing(self):
        pass

class PollCommand(BaseCommand) :
    def to_dict(self):
        """
        @return dict representation of the object
        """
        res = {'id': self.id, 'command': self.command, 'parameters': self.parameters}
        if self.timestamp is not None :
            res['timestamp'] = self.timestamp
        if self.user_id is not None :
            res['userId'] = self.user_id
        if self.lifetime is not None :
            res['lifetime'] = self.lifetime
        if self.flags is not None :
            res['flags'] = self.flags
        if self.status is not None :
            res['status'] = self.status
        if self.result is not None :
            res['result'] = self.result
        return res
    
    @staticmethod
    def create(message) :
        res = PollCommand()
        res.id = message['id']
        res.timestamp = message['timestamp'] if 'timestamp' in message else None
        res.user_id = message['userId'] if 'userId' in message else None
        res.command = message['command']
        res.parameters = message['parameters'] if 'parameters' in message else []
        res.lifetime = message['lifetime'] if 'lifetime' in message else None
        res.flags = message['flags'] if 'flags' in message else None
        res.status = message['status'] if 'status' in message else None
        res.result = message['result'] if 'result' in message else None
        return res


class BaseRequest(Request):
    """
    L{BaseRequest} implements base HTTP/1.1 request
    """
    
    def __init__(self, device_info, method, url, host, api, body_producer = None):
        headers = BaseRequest.headers(host, device_info.id, device_info.key)
        path = url_path(url, api)
        LOG_MSG('{0} PATH {1}'.format(method, path))
        super(BaseRequest, self).__init__(method, path, headers, body_producer)
    
    @staticmethod
    def headers(host, device_id, device_key):
        headers = Headers({'Host': [host.encode('utf-8')],
                           'Content-Type': ['application/json',],
                           'Auth-DeviceID': [device_id.encode('utf-8')],
                           'Auth-DeviceKey': [device_key.encode('utf-8')],
                           'Accept': ['application/json']})
        return headers


class RegisterRequest(BaseRequest):
    """
    L{RegisterRequest} implements register Device-Hive api v6. It is NOT
    intended for an external use.
    """
    
    def __init__(self, device_info, url, host):
        super(RegisterRequest, self).__init__(device_info, 'PUT', url, host, 'device/{0:s}'.format(device_info.id), JsonDataProducer(device_info.to_dict()))


class CommandRequest(BaseRequest):
    """
    L{CommandRequest} sends poll request to a server. The first poll request
    does not contain timestamp field in this case server will use
    current time in UTC.
    """
    def __init__(self, device_info, url, host, timestamp):
        if timestamp is None :
            api = 'device/{0}/command/poll'.format(device_info.id)
        else :
            api = 'device/{0}/command/poll?timestamp={1}'.format(device_info.id, timestamp.isoformat())
        super(CommandRequest, self).__init__(device_info, 'GET', url, host, api)


class ReportRequest(BaseRequest):
    def __init__(self, device_info, url, host, command_id, result):
        super(ReportRequest, self).__init__(device_info,
            'PUT',
            url,
            host,
            'device/{0}/command/{1}'.format(device_info.id, command_id),
            JsonDataProducer(result.to_dict()))


class NotifyRequest(BaseRequest):
    def __init__(self, device_info, url, host, notification, parameters):
        super(NotifyRequest, self).__init__(device_info, 'POST', url, host,
            'device/{0}/notification'.format(device_info.id),
            JsonDataProducer({'notification': notification, 'parameters': parameters}))


class RequestProtocol(HTTP11ClientProtocol):
    def __init__(self, req, deferred):
        if hasattr(HTTP11ClientProtocol, '__init__') :
            HTTP11ClientProtocol.__init__(self)
        self.req = req
        self.deferred = deferred

    def connectionMade(self):
        LOG_MSG('Sending {0} request to devicehive server.'.format(self.req))
        self.request(self.req).addCallbacks(self.on_success, self.on_failure)

    def get_response_text(self, response, func):
        def on_get_response_text(txt):
            func(txt)
        d = Deferred()
        d.addBoth(on_get_response_text)
        response.deliverBody(TextDataConsumer(d))

    def on_success(self, response):
        if response.code in [200, 201] :
            def on_data(txt):
                self.deferred.callback(txt)
            self.get_response_text(response, on_data)
        elif response.code == 204 :
            self.deferred.callback(None)
        else :
            def on_err(err):
                self.deferred.errback(err)
            self.get_response_text(response, on_err)

    def on_failure(self, reason):
        self.deferred.errback(reason)


class RequestFactory(ClientFactory):
    """
    This factory is used to create and send single HTTP/1.1 request.
    """
    
    def __init__(self, req, ok, err):
        if hasattr(ClientFactory, '__init__') :
            ClientFactory.__init__(self)
        self.req = req
        self.ok = ok
        self.err = err
    
    def buildProtocol(self, addr):
        defer = Deferred()
        defer.addCallbacks(self.ok, self.err)
        return RequestProtocol(self.req, defer)


class CommandPollProtocol(HTTP11ClientProtocol):
    """
    CommandPollProtocol sends command-request to the server,
    receives command response or error, pass it for processing and
    finally passes result back to an owner.
    """

    def __init__(self, owner):
        if hasattr(HTTP11ClientProtocol, '__init__'):
            HTTP11ClientProtocol.__init__(self)
        self.owner = owner

    def connectionMade(self):
        LOG_MSG('Sending command poll request for device: {0}.'.format(self.owner.info))
        self.request(CommandRequest(self.owner.info,
                                    self.owner.url,
                                    self.owner.host,
                                    self.owner.timestamp)).addCallbacks(self.success, self.failure)

    def command_failed(self, command, reason):
        """
        This method is called when a client code throws an exception during
        a command processing.

        TODO: replace command dictionary with an object which implements
              ICommand interface.

        TODO: extract 'Success' and 'Failed' constants into common module.

        @param command: a dictionary which represents a command
        @param reason: an exception
        @return: None
        """
        LOG_ERR('Failed to process command "{0}". Reason: {1}.'.format(command, reason))
        if isinstance(reason, Exception):
            res = CommandResult('Failed', reason.message)
        elif hasattr(reason, 'value'):
            if isinstance(reason.value, CommandResult):
                res = CommandResult(reason.value.status, reason.value.result)
            elif isinstance(reason.value, Exception):
                res = CommandResult('Failed', reason.value.message)
            else:
                res = CommandResult('Failed', reason.value)
        else:
            res = CommandResult('Failed', 'Unhandled Exception')
        self.owner.send_report(command['id'], res)

    def command_done(self, command, result):
        """
        This method is called if client application successfully handled
        received command.
        If a command is handled then a notification will be send to the server.

        @param command: a dictionary which represents a received command
        @param result: a command object
        @return: None
        """
        LOG_MSG('The command "{0}" successfully processed. Result: {1}.'.format(command, result))
        if not isinstance(result, CommandResult):
            res = CommandResult('Success', result)
        else:
            res = result
        self.owner.send_report(command['id'], res)

    def command_received(self, cmd_data):
        LOG_MSG('Poll command got response. Response: {0}.'.format(cmd_data))
        for cmd in cmd_data:
            # Obtain only new commands next time
            cmd_date = parse_date(cmd['timestamp'])
            if self.owner.timestamp is not None:
                self.owner.timestamp = max(self.owner.timestamp, cmd_date)
            else:
                self.owner.timestamp = cmd_date
            # device-application will use this deferred object to notify me about the command progress.
            thiscmd = cmd
            def ok(result):
                self.command_done(thiscmd, result)
            def err(reason):
                self.command_failed(thiscmd, reason)
            defer = Deferred()
            defer.addCallbacks(ok, err)
            try:
                LOG_MSG('Executing command {0} handler.'.format(cmd))
                self.owner.run_command(cmd, defer)
            except Exception, err:
                LOG_ERR('Failed to execute device-delegate on_command. Reason: <{0}>.'.format(err))
                self.command_failed(cmd, err)

    def success(self, response):
        LOG_MSG('Got command poll response from the server for device {0}.'.format(self.owner.info))
        if response.code in [200, 201]:
            def err(reason):
                LOG_ERR('Failed to parse command request response. Reason: <{0}>.'.format(reason))
                self.failure(reason)
            result = Deferred()
            result.addCallbacks(self.command_received, err)
            response.deliverBody(JsonDataConsumer(result))
        else:
            def on_get_response_text(error_text):
                LOG_ERR('Invalid response has been received during command polling. Reason: {0}.'.format(error_text))
                self.failure(DhError(error_text))
            d = Deferred()
            d.addBoth(on_get_response_text)
            response.deliverBody(TextDataConsumer(d))

    def failure(self, reason):
        LOG_ERR('Failed to poll devicehive server for a command. Reason: {0}.'.format(reason))
        self.owner.failure(reason)


class DevicePollFactory(ClientFactory):
    proto = None
    recall = None
    
    def __init__(self, owner, info, deferred):
        if not IPollOwner.implementedBy(owner.__class__) :
            raise TypeError('owner has to implement IPollOwner interface.')
        self.owner = owner
        self.timestamp = self.owner.timestamp
        self.info = info
        self.deferred = deferred
        self.connected = False
        self.stopped = False
    
    url = property(fget = lambda self : self.owner.url)
    
    host = property(fget = lambda self : self.owner.host)
    
    port = property(fget = lambda self : self.owner.port)
    
    def buildProtocol(self, addr):
        LOG_MSG('Building devicehive command poll protocol object.')
        self.proto = CommandPollProtocol(self)
        return self.proto
    
    def clientConnectionSuccess(self):
        LOG_MSG('Client has connected to devicehive server.')
        if not self.connected :
            self.connected = True
            self.deferred.callback(self.info)
    
    def clientConnectionFailed(self, connector, reason):
        LOG_ERR('Client failed to connect to devicehive server.')
        if not self.connected :
            self.deferred.errback(reason)
    
    def clientConnectionLost(self, connector, reason):
        LOG_ERR('Client has lost command poll connection to the devicehive server.')
        def reconnect(connector) :
            connector.connect()
        if not self.stopped :
            LOG_MSG('Reconnecting client {0} to the server {1}:{2}.'.format(self.info, self.url, self.host))
            self.recall = reactor.callLater(self.owner.poll_interval, reconnect, connector)
    
    def stop(self):
        """ Stops command polling. """
        # TODO: test this method (how it works)
        self.stop_requested = True
        if (self.recall is not None) and self.recall.active() :
            self.recall.cancel()
        if (self.proto is not None) and (self.proto.transport.connector.state == 'connected') :
            self.proto.transport.loseConnection()
    
    def __repr__(self):
        return '<{0} for device {1}>'.format(self.__class__.__name__, self.info)
    
    def send_report(self, cmdid, cmdres):
        """ Sends command result of a command been invoked to devicehive server. """
        def ok(result):
            LOG_MSG('Command {0} result has been sent.'.format(cmdid))
        def err(reason):
            LOG_MSG('Failed to send command {0} result. Reason: {1}.'.format(cmdid, reason))
        factory = RequestFactory(ReportRequest(self.info, self.url, self.host, cmdid, cmdres), ok, err)
        reactor.connectDeviceHive(self.url, factory)
    
    def run_command(self, cmd, fin_defer):
        """ Executes user command handler. """
        self.owner.on_command(self.info, cmd, fin_defer)
    
    def failure(self, reason):
        self.owner.on_failure(self.info.id, reason)


class PollFactory(object):
    implements(IProtoFactory, IPollOwner)
    
    url = 'http://localhost'
    host = 'localhost'
    port = 80
    timestamp = None
    poll_interval = 1.0
    
    def __init__(self, handler):
        if not IProtoHandler.implementedBy(handler.__class__) :
            raise TypeError('handler has to implement devicehive.interfaces.IProtoHandler interface.')
        self.handler = handler
        self.handler.factory = self
        self.devices = {}
        self.factories = {}
        self.timestamp = datetime.utcnow()
    
    def execute_request(self, request, ok, err):
        factory = RequestFactory(request, ok, err)
        reactor.connectDeviceHive(self.url, factory)
    
    # begin IPollOwner implementation
    def on_command(self, info, cmd, finish):
        if info.id in self.devices :
            self.handler.on_command(info.id, PollCommand.create(cmd), finish)
        else :
            raise ValueError('Device {0} is not registered.'.format(info.id))
    
    def on_failure(self, device_id, reason):
        if device_id in self.devices :
            self.handler.on_failure(device_id, reason)
    # end IPollOwner
    
    # begin IProtoFactory implementation
    def authenticate(self, device_id, device_key):
        raise NotImplementedError()
    
    def notify(self, notification, params, device_id = None, device_key = None):
        if (device_id is not None) and (device_id in self.devices) :
            defer = Deferred()
            def ok(res):
                LOG_MSG('Notification has been successfully sent.')
                defer.callback(res)
            def err(reason):
                LOG_ERR('Failed to send notification.')
                defer.errback(reason)
            self.execute_request(NotifyRequest(self.devices[device_id], self.url, self.host, notification, params), ok, err)
            return defer
        else :
            return fail(DhError('device_id parameter expected'))
    
    def subscribe(self, device_id = None, device_key = None):
        if device_id in self.devices :
            defer = Deferred()
            factory = DevicePollFactory(self, self.devices[device_id], defer)
            self.factories[device_id] = factory
            LOG_MSG('Connecting command poll factory to {0}:{1}.'.format(self.host, self.port))
            reactor.connectDeviceHive(self.url, factory)
            return defer
        else :
            return fail(DhError('Failed to subscribe device "{0}".'.format(device_id)))
    
    def unsubscribe(self, device_id = None, device_key = None):
        if (device_id in self.devices) and (device_id in self.factories) :
            factory = self.factories.pop(device_id)
            return factory.stop()
        else :
            return fail(DhError('device_id parameter expected'))
    
    def device_save(self, info):
        self.devices[info.id] = info
        defer = Deferred()
        def registration_success(result):
            LOG_MSG('Device has been saved. Info: {0}.'.format(info))
            defer.callback(info)
        def registration_failure(reason):
            LOG_MSG('Failed to save device. Info: {0}.'.format(info))
            defer.errback(reason)
        req = RegisterRequest(info, self.url, self.host)
        self.execute_request(req, registration_success, registration_failure)
        return defer
    
    def connect(self, url):
        LOG_MSG('PollFactory: Connection with {0} has been established.'.format(url))
        self.url, self.host, self.port = parse_url(url)
        self.handler.on_connected()
    # end IProtoFactory implementation
