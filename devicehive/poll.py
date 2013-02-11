# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8 encoding=utf-8:

import json
from functools import partial
from sys import maxint
from zope.interface import implements, Interface, Attribute
from twisted.python import log
from twisted.python.constants import Values, ValueConstant
from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory, Protocol
from twisted.internet.defer import Deferred, succeed, fail
from twisted.web.iweb import IBodyProducer
from twisted.web.client import HTTP11ClientProtocol, Request
from twisted.web.http_headers import Headers
from urlparse import urlsplit, urljoin
from utils import parse_url, parse_date, url_path
from interfaces import IProtoFactory, IProtoHandler
from devicehive import ApiInfoRequest, DhError, CommandResult
from devicehive.utils import TextDataConsumer


__all__ = ['JsonDataProducer', 'JsonDataConsumer', 'BaseRequest', 'RegisterRequest', 'NotifyRequest', 'ReportRequest', 'CommandRequest', 'PollFactory']


class ICommandHandler(Interface):
    def on_command(self, cmd, finish):
        """
        @type cmd: C{dict}
        @param cmd: command
        
        @type finish: C{Defer}
        @param finish: a user has to callback this deferred in order to signal to the library that commad has been processed.
        """


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


class JsonDataProducer(object):
    """
    L{JsonDataProducer}. This class is not intended for external use.
    """
    implements(IBodyProducer)

    def __init__(self, data):
        self.finished = Deferred()
        self.data = json.dumps(data)
        self.length = len(self.data)

    def startProducing(self, consumer):
        self.consumer = consumer
        self.consumer.write(self.data)
        return self.finished

    def stopProducing(self):
        pass


class JsonDataConsumer(Protocol):
    """
    L{JsonDataConsumer}
    """

    def __init__(self, deferred):
        self.deferred = deferred
        self.data = []

    def dataReceived(self, data):
        self.data.append(data)

    def connectionLost(self, reason):
        data = json.loads(''.join(self.data))
        self.deferred.callback(data)


class BaseRequest(Request):
    """
    L{BaseRequest} implements base HTTP/1.1 request
    """
    
    def __init__(self, factory, method, api, body_producer = None):
        headers = BaseRequest.headers(factory.host, factory.info.id, factory.info.key)
        path = url_path(factory.url, api)
        super(BaseRequest, self).__init__(method, path, headers, body_producer)
    
    @staticmethod
    def headers(host, device_id, device_key):
        headers = Headers({'Host': [host],
                           'Content-Type': ['application/json',],
                           'Auth-DeviceID': [device_id],
                           'Auth-DeviceKey': [device_key],
                           'Accept': ['application/json']})
        return headers


class RegisterRequest(BaseRequest):
    """
    L{RegisterRequest} implements register Device-Hive api v6. It is NOT
    intended for an external use.
    """
    
    def __init__(self, factory):
        super(RegisterRequest, self).__init__(factory, 'PUT', 'device/{0:s}'.format(factory.info.id), JsonDataProducer(factory.info.to_dict()))


class CommandRequest(BaseRequest):
    """
    L{CommandRequest} sends poll request to a server. The first poll request
    does not contain timestamp field in this case server will use
    current time in UTC.
    """
    def __init__(self, factory):
        if factory.timestamp is None :
            url = 'device/{0}/command/poll'.format(factory.info.id)
        else :
            url = 'device/{0}/command/poll?timestamp={1}'.format(factory.info.id, factory.timestamp.isoformat())
        super(CommandRequest, self).__init__(factory, 'GET', url)


class ReportRequest(BaseRequest):
    def __init__(self, factory, command, result):
        super(ReportRequest, self).__init__(factory,
            'PUT',
            'device/{0}/command/{1}'.format(factory.info.id, command['id']),
            JsonDataProducer(result.to_dict()))


class NotifyRequest(BaseRequest):
    def __init__(self, factory, notification, parameters):
        super(NotifyRequest, self).__init__(factory,
            'POST',
            'device/{0}/notification'.format(factory.info.id),
            JsonDataProducer({'notification': notification, 'parameters': parameters}))


class ProtocolState(Values) :
    """
    Class is not intended for external use.
    """
    Unknown  = ValueConstant(0)
    Register = ValueConstant(1)
    Command  = ValueConstant(2)
    Notify   = ValueConstant(3)
    Report   = ValueConstant(4)


class ReportData(object):
    def __init__(self, command, result):
        self._command = command
        self._result  = result
    command = property(fget = lambda self : self._command)
    result  = property(fget = lambda self : self._result)


class NotifyData(object):
    def __init__(self, notification, parameters):
        self._notification = notification
        self._parameters = parameters
    notification = property(fget = lambda self : self._notification)
    parameters = property(fget = lambda self : self._parameters)


class StateHolder(object):
    """
    TODO: Incapsulate all retry logic into state holder
    """
    def __init__(self, state, state_data = None, retries = 0) :
        self._state = state
        self._data = state_data
        self._retries = retries
        self._do_retry = False
    
    value    = property(fget = lambda self : self._state)
    
    data     = property(fget = lambda self : self._data)
    
    def retries():
        def fget(self):
            return self._retries
        def fset(self, value):
            self._retries = value
        return locals()
    retries = property(**retries())
    
    def do_retry():
        def fget(self):
            return self._do_retry
        def fset(self, value):
            self._do_retry = value
        return locals()
    do_retry = property(**do_retry())


class _ReportHTTP11DeviceHiveProtocol(HTTP11ClientProtocol):
    """
    L{_ReportHTTP11DeviceHiveProtocol} sends one report request to device-hive server.
    """

    def __init__(self, factory):
        if hasattr(HTTP11ClientProtocol, '__init__'):
            # fix for cygwin twisted distribution
            HTTP11ClientProtocol.__init__(self)
        self.factory = factory
        
    def connectionMade(self):
        req = self.request(ReportRequest(self.factory.owner, self.factory.state.data.command, self.factory.state.data.result))
        req.addCallbacks(self._report_done, self._critical_error)
    
    def _report_done(self, response):
        if response.code == 200 :
            log.msg('Report <{0}> response for received.'.format(self.factory.state.data))
        else :
            def get_response_text(reason):
                log.err('Failed to get report-request response. Response: <{0}>. Code: <{1}>. Reason: <{2}>.'.format(response, response.code, reason))
            response_defer = Deferred()
            response_defer.addCallbacks(get_response_text, get_response_text)
            response.deliverBody(TextDataConsumer(response_defer))
            self.factory.retry(self.transport.connector)
    
    def _critical_error(self, reason):
        log.err("Device-hive report-request failure. Critical error: <{0}>".format(reason))
        if reactor.running :
            if callable(self.factory.on_failure) :
                self.factory.on_failure()
        pass


class _NotifyHTTP11DeviceHiveProtocol(HTTP11ClientProtocol):
    """
    L{_NotifyHTTP11DeviceHiveProtocol} sends one notification request.
    """
    def __init__(self, factory):
        if hasattr(HTTP11ClientProtocol, '__init__'):
            # fix for cygwin twisted distribution
            HTTP11ClientProtocol.__init__(self)
        self.factory = factory
    
    def connectionMade(self):
        req = self.request(NotifyRequest(self.factory.owner, self.factory.state.data.notification, self.factory.state.data.parameters))
        req.addCallbacks(self._notification_done, self._critical_error)
    
    def _notification_done(self, response):
        if response.code == 201:
            log.msg('Notification <{0}> response for received.'.format(self.factory.state.data))
        else :
            def get_response_text(reason):
                log.err('Failed to get notification-request response. Response: <{0}>. Code: <{1}>. Reason: <{2}>.'.format(response, response.code, reason))
            response_defer = Deferred()
            response_defer.addCallbacks(get_response_text, get_response_text)
            response.deliverBody(TextDataConsumer(response_defer))
            self.factory.retry(self.transport.connector)
    
    def _critical_error(self, reason):
        log.err("Device-hive notify-request failure. Critical error: <{0}>".format(reason))
        if reactor.running :
            if callable(self.factory.on_failure) :
                self.factory.on_failure()
        pass


class HTTP11DeviceHiveProtocol(HTTP11ClientProtocol):
    """
    L{HTTP11DeviceHiveProtocol} represent device hive protocol.

    @ivar factory Reference to DeviceHiveFactory instance
    """

    def __init__(self, factory):
        if hasattr(HTTP11ClientProtocol, '__init__'):
            HTTP11ClientProtocol.__init__(self)
        self.factory = factory

    def connectionMade(self):
        if self.factory.state.value == ProtocolState.Register :
            self.request(RegisterRequest(self.factory)).addCallbacks(self._register_done, self._critical_error)
        elif self.factory.state.value == ProtocolState.Command :
            res = self.request(CommandRequest(self.factory))
            res.addCallbacks(self._command_done, self._critical_error)
        else :
            log.err("Unsupported device-hive protocol state <{0}>.".format(self.factory.state.value))
            if callable(self.factory.on_failure) :
                self.factory.on_failure()
            pass
    
    def _critical_error(self, reason):
        """
        Any critical error will stop reactor.
        """
        log.err("Device-hive protocol failure. Critical error: <{0}>".format(reason))
        if reactor.running :
            if callable(self.factory.on_failure) :
                self.factory.on_failure()
        pass
    
    def _register_done(self, response):
        """
        Method is called when the answer to registration request is received.
        """
        if response.code == 200:
            def get_response_text(reason):
                log.err('Registration succeed. Response code {0}. Reason: {1}.'.format(response.code, reason))
            response_defer = Deferred()
            response_defer.addCallbacks(get_response_text, get_response_text)
            response.deliverBody(TextDataConsumer(response_defer))
            
            self.factory.registered = True
            self.factory.next_state(ProtocolState.Command, connector = self.transport.connector)
        else :
            def get_response_text(reason):
                log.err('Registration failed. Response code {0}. Reason: {1}.'.format(response.code, reason))
            response_defer = Deferred()
            response_defer.addCallbacks(get_response_text, get_response_text)
            response.deliverBody(TextDataConsumer(response_defer))
            self.factory.retry(self.transport.connector)
    
    def _command_done(self, response):
        if response.code == 200 :
            def get_response(cmd_data):
                for cmd in cmd_data :
                    def __command_done(result, command) :
                        res = result
                        if not isinstance(result, CommandResult) :
                            res = CommandResult(status = result)
                        self.factory.next_state(ProtocolState.Report, ReportData(command, res), self.transport.connector)
                    ok_func = partial(__command_done, command = cmd)
                    def __command_error(reason, command):
                        res = CommandResult('Failed', str(reason))
                        self.factory.next_state(ProtocolState.Report, ReportData(command, res), self.transport.connector)
                    err_func = partial(__command_error, command = cmd)
                    # Obtain only new commands next time
                    if self.factory.timestamp is not None :
                        self.factory.timestamp = max(self.factory.timestamp, parse_date(cmd['timestamp']))
                    else :
                        self.factory.timestamp = parse_date(cmd['timestamp'])
                    # DeviceDelegate has to use this deferred object to notify us that command processing finished.
                    cmd_defer = Deferred()
                    cmd_defer.addCallbacks(ok_func, err_func)
                    # Actual run of command
                    try :
                        self.factory.on_command(cmd, cmd_defer)
                    except Exception, err :
                        log.err('Failed to execute device-delegate on_command. Reason: <{0}>.'.format(err))
                        err_func(err)
                self.factory.next_state(ProtocolState.Command, connector = self.transport.connector)
            def err_response(reason):
                log.err('Failed to parse command request response. Reason: <{0}>.'.format(reason))
                self.factory.next_state(ProtocolState.Command, connector = self.transport.connector)
            result_proto = Deferred()
            result_proto.addCallbacks(get_response, err_response)
            response.deliverBody(JsonDataConsumer(result_proto))
        else :
            log.err('Failed to get command request response. Response: <{0}>. Code: <{1}>.'.format(response, response.code))
            self.factory.retry(self.transport.connector)


class ApiInfoProtocol(HTTP11ClientProtocol):
    
    def __init__(self, factory):
        HTTP11ClientProtocol.__init__(self)
        self.factory = factory
    
    def connectionMade(self):
        self.request(ApiInfoRequest(self.factory.url, self.factory.host)).addCallbacks(self.on_ok, self.on_fail)
    
    def on_ok(self, response):
        if response.code == 200:
            def ok_response(obj):
                url, host, port = parse_url(obj['webSocketServerUrl'])
                server_time = parse_date(obj['serverTimestamp'])
                self.factory.api_received(url, host, port, server_time)
            
            def err_response(reason):
                log.err('Failed to parse command request response. Reason: <{0}>.'.format(reason))
            
            res = Deferred()
            res.addCallbacks(ok_response, err_response)
            response.deliverBody(JsonDataConsumer(res))
        else :
            log.err('API Info failed. Response code: {0}.'.format(response.code))
    
    def on_fail(self, reason):
        log.err('Failed to make API Info request. Reason: {0}.'.format(reason))



class BaseHTTP11ClientFactory(ClientFactory):
    """
    This L{ReconnectFactory} uses different approach to reconnect than
    Twisted`s L{ReconnectClientFactory}.

    @ivar state Indicates what state this L{DeviceHiveFactory} instance
        is in with respect to Device-Hive protocol v6.
    @ivar retries In case of failure, DeviceHiveProtocol instance will try to
        resend last command L{retries} count times.
    """
    def __init__(self, state, retries):
        self.retries = retries
        self.state = state
        self.started = False
    
    def doStart(self) :
        ClientFactory.doStart(self)
        self.started = True
    
    def clientConnectionLost(self, connector, reason):
        self.handleConnectionLost(connector)
        self.started = False
    
    def handleConnectionLost(self, connector):
        def reconnect(connector) :
            connector.connect()
        if self.state.do_retry :
            self.state.retries -= 1
            self.state.do_retry = False
            reconnect(connector)
            return True
        return False
    
    def retry(self, connector = None):
        if self.state.retries > 0 :
            self.state.do_retry = True
        if (not self.started) and (connector is not None) and (connector.state == 'disconnected') :
            self.handleConnectionLost(connector)
    
    def notify(self, notification, kwargs):
        raise NotImplementedError()


class _SingleRequestHTTP11DeviceHiveFactory(BaseHTTP11ClientFactory):
    """
    This factory is used to create and send single HTTP/1.1 request.
    """
    def __init__(self, owner, state, retries):
        BaseHTTP11ClientFactory.__init__(self, state, retries)
        self.owner = owner
    
    def buildProtocol(self, addr):
        if self.state.value == ProtocolState.Report :
            return _ReportHTTP11DeviceHiveProtocol(self)
        elif self.state.value == ProtocolState.Notify :
            return _NotifyHTTP11DeviceHiveProtocol(self)
        else :
            raise NotImplementedError('Unsupported factory state <{0}>.'.format(self.state.value))


class DevicePollFactory(BaseHTTP11ClientFactory):
    
    implements(ICommandHandler)

    def __init__(self, owner, info, poll_interval = 1.0, retries = 3):
        BaseHTTP11ClientFactory.__init__(self, StateHolder(ProtocolState.Unknown), retries)
        self.owner = owner
        self.info = info
        self.poll_interval = poll_interval
        self.retries = retries
        # for internal usage
        self.registered = False
        self.states_stack = []
        self.timestamp = self.owner.timestamp
    
    url = property(fget = lambda self : self.owner.url)
    
    host = property(fget = lambda self : self.owner.host)
    
    def test_owner(self):
        return IPollOwner.implementedBy(self.owner.__class__)
    
    def doStart(self) :
        if self.state.value == ProtocolState.Unknown :
            self.state = StateHolder(ProtocolState.Register)
        BaseHTTP11ClientFactory.doStart(self)
    
    def buildProtocol(self, addr):
        return HTTP11DeviceHiveProtocol(self)
    
    def handleConnectionLost(self, connector):
        def reconnect(connector) :
            connector.connect()
        if (not BaseHTTP11ClientFactory.handleConnectionLost(self, connector)) and (self.registered):
            # Because Registration is a very first thing which is invoked I do not
            # need to add an addition verification here
            if len(self.states_stack) > 0 :
                tmp_state = self.states_stack.pop(0)
                # If user made a bunch of notifications before device got registered
                # we send them all here at one go
                while tmp_state.value == ProtocolState.Notify :
                    self.single_request(tmp_state)
                    tmp_state = None
                    if len(self.states_stack) > 0 :
                        tmp_state = self.states_stack.pop(0)
                    else :
                        return
                # In current implementation this could be only ProtocolState.Command
                if tmp_state is not None :
                    self.state = tmp_state
                    reactor.callLater(self.poll_interval, reconnect, connector)
        pass
    
    def notify(self, notification, kwargs) :
        self.next_state(ProtocolState.Notify, data = NotifyData(notification, kwargs))
    
    def next_state(self, next_state, data = None, connector = None) :
        if self.registered and (next_state == ProtocolState.Notify or next_state == ProtocolState.Report) :
            self.single_request(StateHolder(next_state, data))
        else :
            self.states_stack.append(StateHolder(next_state, data, self.retries))
            if (not self.started) and (connector is not None) and (connector.state == 'disconnected') :
                self.handleConnectionLost(connector)
    
    def single_request(self, state):
        subfactory = _SingleRequestHTTP11DeviceHiveFactory(self, state, self.retries)
        reactor.connectTCP(self.owner.host, self.owner.port, subfactory)
    
    def on_failure(self):
        log.msg('Protocol failure. Stopping reactor.')
    
    def on_command(self, cmd, finished):
        self.owner.on_command(self.info, cmd, finished)
    
    def __repr__(self):
        return '<{0} for device {1}>'.format(self.__class__.__name__, self.info)


class PollFactory(ClientFactory):
    
    implements(IProtoFactory, IPollOwner)
    
    url  = 'http://localhost'
    host = 'localhost'
    port = 80
    timestamp = None
    
    poll_interval = 1.0
    retries = 3
    
    def __init__(self, handler):
        self.handler = handler
        if self.test_handler() :
            self.handler.factory = self
        self.devices = {}
        self.factories = {}
    
    def test_handler(self):
        return IProtoHandler.implementedBy(self.handler.__class__)
    
    def buildProtocol(self, addr):
        return ApiInfoProtocol(self)
    
    # begin callbacks
    def api_received(self, url, host, port, server_time):
        self.timestamp = server_time
        if self.test_handler() :
            # for long-polling api, "receiving api info" and "connection" events
            # mean the same.
            self.handler.on_apimeta(self.url, self.timestamp)
            self.handler.on_connected()
    # end callbacks
    
    # begin IPollOwner implementation
    def on_command(self, info, cmd, finish):
        if (info.id in self.devices) and self.test_handler() :
            self.handler.on_command(info.id, cmd, finish)
    # end IPollOwner
    
    # begin IProtoFactory implementation
    def authenticate(self, device_id, device_key):
        """
        Sends authentication message.
        
        @param device_id - device id
        @param device_key - device key
        @return deferred
        """
    
    def notify(self, notification, params, device_id = None, device_key = None):
        if (device_id is not None) and (device_id in self.factories) :
            factory = self.factories[device_id]
            factory.notify(notification, params)
            return succeed(None)
        else :
            return fail(DhError('device_id parameter expected'))
    
    def update_command(self, command, device_id = None, device_key = None):
        """
        Updates an existing device command.
        
        @return deferred
        """
    
    def subscribe(self, device_id = None, device_key = None):
        if device_id in self.devices :
            factory = DevicePollFactory(self, self.devices[device_id])
            self.factories[device_id] = factory
            return reactor.connectTCP(self.host, self.port, factory)
        else :
            return fail(DhError('Failed to subscribe device "{0}".'.format(device_id)))
    
    def unsubscribe(self, device_id = None, device_key = None):
        """
        Unsubscribe a device from commands reception.
        
        @type device_id
        
        @return deferred
        """
    
    def device_save(self, info):
        self.devices[info.id] = info
        return succeed(info)
    # end IProtoFactory implementation

