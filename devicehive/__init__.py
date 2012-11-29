# vim: set et tabstop=4 shiftwidth=4 nu nowrap: fileencoding=utf-8 encoding=utf-8


import json
from functools import partial
from datetime import datetime
from zope.interface import implements
from twisted.python import log
from twisted.python.constants import Values, ValueConstant
from twisted.internet.protocol import ClientFactory, Protocol
from twisted.web.client import HTTP11ClientProtocol, Request
from twisted.internet.defer import Deferred
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer
from twisted.internet import reactor
from urlparse import urlsplit, urljoin


__all__ = ['HTTP11DeviceHiveFactory', 'DeviceDelegate', 'Equipment', 'CommandResult']


def parse_url(device_hive_url):
	if not device_hive_url.endswith('/'):
		device_hive_url += '/'
	url = urlsplit(device_hive_url)
	netloc_split = url.netloc.split(':')
	port = 80
	host = netloc_split[0]
	if url.scheme == 'https':
		port = 443
	if len(netloc_split) == 2:
		port = int(netloc_split[1], 10)
	return (device_hive_url, host, port)


def connectDeviceHive(device_hive_url, factory):
	"""
	reactor.connectDeviceHive(device_hive_url, factory)
	"""
	url, host, port = parse_url(device_hive_url)
	factory.uri = url
	factory.host = host
	factory.port = port
	return reactor.connectTCP(host, port, factory)
reactor.connectDeviceHive = connectDeviceHive


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


class TextDataConsumer(Protocol):
	def __init__(self, deferred):
		self.deferred = deferred
		self.text = ''
	def dataReceived(self, data):
		self.text += data
	def connectionLost(self, reason):
		self.deferred.callback(self.text)


class BaseRequest(Request):
	"""
	L{BaseRequest} implements base HTTP/1.1 request
	"""

	def __init__(self, factory, method, api_uri, body_producer = None):
		netloc, api_path = BaseRequest.get_urls(factory.uri, api_uri)
		headers = self.default_headers(factory.host, factory.device_delegate.device_id(), factory.device_delegate.device_key())
		super(BaseRequest, self).__init__(method, api_path, headers, body_producer)

	def default_headers(self, host, device_id, device_key):
		headers = Headers({'Host': [host,],
							'Content-Type': ['application/json',],
                   			'Auth-DeviceID': [device_id,],
							'Auth-DeviceKey': [device_key,],
							'Accept': ['application/json',]})
		return headers

	@staticmethod
	def get_urls(base_uri, api_uri):
		uri = urlsplit(urljoin(base_uri, api_uri))
		api_path = uri.path
		if len(uri.query) > 0 :
			api_path += '?' + uri.query
		return (uri.netloc, api_path)


class RegisterRequest(BaseRequest):
	"""
	L{RegisterRequest} implements register Device-Hive api v6. It is NOT
	intended for an external use.
	"""

	def __init__(self, factory):
		super(RegisterRequest, self).__init__(factory,
						'PUT',
						'device/{0:s}'.format(factory.device_delegate.device_id()),
						JsonDataProducer(factory.device_delegate.registration_info()))


class CommandRequest(BaseRequest):
	"""
	L{CommandRequest} sends poll request to a server. The first poll request
	does not contain timestamp field in this case server will use
	current time in UTC.
	"""
	def __init__(self, factory):
		if factory.timestamp is None :
			url = 'device/{0}/command/poll'.format(factory.device_delegate.device_id())
		else :
			url = 'device/{0}/command/poll?timestamp={1}'.format(factory.device_delegate.device_id(), factory.timestamp.isoformat())
		super(CommandRequest, self).__init__(factory, 'GET', url)


class ReportRequest(BaseRequest):
	def __init__(self, factory, command, result):
		super(ReportRequest, self).__init__(factory,
			'PUT',
			'device/{0}/command/{1}'.format(factory.device_delegate.device_id(), command['id']),
			JsonDataProducer(result.to_dict()))


class NotifyRequest(BaseRequest):
	def __init__(self, factory, notification, parameters):
		super(NotifyRequest, self).__init__(factory,
			'POST',
			'device/{0}/notification'.format(factory.device_delegate.device_id()),
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


class CommandResult(object):
	def __init__(self, status, result = None):
		self._status = status
		self._result = result
	def to_dict(self):
		if self._result is not None :
			return {'status': str(self._status), 'result': str(self._result)}
		else :
			return {'status': str(self._status)}
	status = property(fget = lambda self : self._status)
	result = property(fget = lambda self : self._result)


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
		req.addCallback(self._report_done)
		req.addErrback(self._critical_error)

	def _report_done(self, response):
		if response.code == 200 :
			log.msg('Report <{0}> response for received.'.format(self.factory.state.data))
		else :
			def get_response_text(reason):
				log.err('Failed to get report-request response. Response: <{0}>. Code: <{1}>. Reason: <{2}>.'.format(response, response.code, reason))
			response_defer = Deferred()
			response_defer.addCallback(get_response_text)
			response_defer.addErrback(get_response_text)
			response.deliverBody(TextDataConsumer(response_defer))
			self.factory.retry(self.transport.connector)

	def _critical_error(self, reason):
		log.err("Device-hive report-request failure. Critical error: <{0}>".format(reason))
		if reactor.running :
			reactor.stop()


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
		req.addCallback(self._notification_done)
		req.addErrback(self._critical_error)

	def _notification_done(self, response):
		if response.code == 201:
			log.msg('Notification <{0}> response for received.'.format(self.factory.state.data))
		else :
			def get_response_text(reason):
				log.err('Failed to get notification-request response. Response: <{0}>. Code: <{1}>. Reason: <{2}>.'.format(response, response.code, reason))
			response_defer = Deferred()
			response_defer.addCallback(get_response_text)
			response_defer.addErrback(get_response_text)
			response.deliverBody(TextDataConsumer(response_defer))
			self.factory.retry(self.transport.connector)

	def _critical_error(self, reason):
		log.err("Device-hive notify-request failure. Critical error: <{0}>".format(reason))
		if reactor.running :
			reactor.stop()


class HTTP11DeviceHiveProtocol(HTTP11ClientProtocol):
	"""
	L{HTTP11DeviceHiveProtocol} represent device hive protocol.

	@ivar factory Reference to DeviceHiveFactory instance
	"""

	def __init__(self, factory):
		if hasattr(HTTP11ClientProtocol, '__init__'):
			# fix for cygwin twisted distribution
			HTTP11ClientProtocol.__init__(self)
		self.factory = factory

	def connectionMade(self):
		log.msg('Connection: {0}.'.format(self.factory.state.value))
		if self.factory.state.value == ProtocolState.Register :
			res = self.request(RegisterRequest(self.factory))
			res.addCallback(self._register_done)
			res.addErrback(self._critical_error)
		elif self.factory.state.value == ProtocolState.Command :
			res = self.request(CommandRequest(self.factory))
			res.addCallback(self._command_done)
			res.addErrback(self._critical_error)
		else :
			log.err("Unsupported device-hive protocol state <{0}>.".format(self.factory.state.value))
			reactor.stop()

	def _critical_error(self, reason):
		"""
		Any critical error will stop reactor.
		"""
		log.err("Device-hive protocol failure. Critical error: <{0}>".format(reason))
		if reactor.running :
			reactor.stop()

	def _register_done(self, response):
		"""
		Method is called when the answer to registration request is received.
		"""
		if response.code == 200:
			log.msg('Registration has been done.')
			self.factory.registered = True
			self.factory.registration_finished.callback(response)
			self.factory.next_state(ProtocolState.Command, connector = self.transport.connector)
		else :
			def get_response_text(reason):
				log.err('Registration failed. Response: <{0}>. Code <{1}>. Reason: <{2}>.'.format(response, response.code, reason))
			response_defer = Deferred()
			response_defer.addCallback(get_response_text)
			response_defer.addErrback(get_response_text)
			response.deliverBody(TextDataConsumer(response_defer))
			self.factory.registration_finished.errback(response)
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
						self.factory.timestamp = max(self.factory.timestamp, self._parse_date(cmd['timestamp']))
					else :
						self.factory.timestamp = self._parse_date(cmd['timestamp'])
					# DeviceDelegate has to use this deferred object to notify us that command processing finished.
					cmd_defer = Deferred()
					cmd_defer.addCallback(ok_func)
					cmd_defer.addErrback(err_func)
					# Actual run of command
					try :
						self.factory.device_delegate.do_command(cmd, cmd_defer)
					except Exception, err :
						log.err('Failed to execute device-delegate do_command. Reason: <{0}>.'.format(err))
						err_func(err)
				self.factory.next_state(ProtocolState.Command, connector = self.transport.connector)
			def err_response(reason):
				log.err('Failed to parse command request response. Reason: <{0}>.'.format(reason))
				self.factory.next_state(ProtocolState.Command, connector = self.transport.connector)
			result_proto = Deferred()
			result_proto.addCallback(get_response)
			result_proto.addErrback(err_response)
			response.deliverBody(JsonDataConsumer(result_proto))
		else :
			log.err('Failed to get command request response. Response: <{0}>. Code: <{1}>.'.format(response, response.code))
			self.factory.retry(self.transport.connector)

	def _parse_date(self, date_str):
		if len(date_str) > 19:
			return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%f')
		else:
			return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')


class Equipment(object):
	"""
	L{Equipment} is an utility class indended to simplify
	device description declaration.
	"""
	def __init__(self, name, code, _type):
		self._name = name
		self._code = code
		self.__type = _type
	name  = property(fget = lambda self : self._name)
	code  = property(fget = lambda self : self._code)
	_type = property(fget = lambda self : self.__type)
	def to_dict(self):
		return {'name': self._name, 'code': self._code, 'type': self._type}


class DeviceDelegate(object):
	"""
	L{DeviceHiveDelegate} is an abstract class. User have to implemenet the following
	methods:
		device_id(self)
		device_key(self)
		device_name(self)
		device_status(self)
		network_name(self)
		network_description(self)
		network_key(self)
		device_class_name(self)
		device_class_version(self)
		device_class_is_permanent(self)
		equipment(self)

		do_command(self, command, finish_deferred)
	"""

	def __init__(self):
		self.factory = None

	def notify(self, notification, **kwargs) :
		"""
		Sends notification to Device-Hive server.
		"""
		if self.factory is not None :
			self.factory.next_state(ProtocolState.Notify, data = NotifyData(notification, kwargs))

	def registration_info(self):
		res = {'id': self.device_id(),
		'key': self.device_key(),
		'name': self.device_name(),
		'status':  self.device_status(),
		'network': {'name': self.network_name(), 'description': self.network_description()},
		'deviceClass': {'name': self.device_class_name(), 'version': self.device_class_version(), 'isPermanent': self.device_class_is_permanent()},
		'equipment': [x.to_dict() for x in self.equipment()]}
		timeout = self.offline_timeout()
		if timeout is not None :
			res['offlineTimeout'] = timeout
		net_key = self.network_key()
		if net_key is not None :
			res['network']['key'] = net_key
		return res

	def offline_timeout(self):
		return None

	def device_id(self):
		"""
		User must override this method in subclass. Method returns device id which
		is a string representation of GUID data type.
		"""
		raise NotImplementedError()

	def device_key(self):
		"""
		User must override this method in subclass. Method returns device key
		which is of string type.
		"""
		raise NotImplementedError()

	def device_name(self):
		raise NotImplementedError()

	def device_status(self):
		raise NotImplementedError()

	def network_name(self):
		raise NotImplementedError()

	def network_description(self):
		raise NotImplementedError()

	def network_key(self):
		"""
		User may override this method in subclass. If method is not
		overridden then no network key will be sent during registration phase.
		"""
		return None

	def device_class_name(self):
		raise NotImplementedError()

	def device_class_version(self):
		raise NotImplementedError()

	def device_class_is_permanent(self):
		"""
		Method has to return boolean value which mean whether this
		device class is permanent or not.
		"""
		raise NotImplementedError()

	def equipment(self):
		"""
		User must override this method in subclass. Method must
		return a list of L{devicehive.Equipment} objects.
		"""
		raise NotImplementedError()

	def do_command(self, command, finish_deferred):
		"""
		Method handles particular command. It has to call finish_deferred.callback(command_result).
		command_result should be of boolean type.
		"""
		raise NotImplementedError()


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


class HTTP11DeviceHiveFactory(BaseHTTP11ClientFactory):
	"""
	L{DeviceHiveFactory} is an implementation of the DeviceHive protocol v6.
	DeviceHiveFactory instance holds protocol state and settings.

	@ivar uri Device Hive URL.
	@ivar host Device Hive server host name.
	@ivar port Device Hive server port number.
	@ivar poll_interval Interval in seconds between requests to device-hive.
	@ivar oneshot Whether factory runs device-hive protocol continiusly or
		one call results in one device-hive request.
	@ivar registered Indicates that protocol has passed registration phase.
	@ivar states_stack Queue used to store required states. It is also used to
		store notification requests before device has registered.
	"""
	def __init__(self, device_delegate, poll_interval = 1.0, retries = 3, oneshot = False):
		BaseHTTP11ClientFactory.__init__(self, StateHolder(ProtocolState.Unknown), retries)
		self.uri  = 'localhost'
		self.host = 'localhost'
		self.port = 80
		self.poll_interval = poll_interval
		self.oneshot = oneshot
		# initialize device-delegate
		self.device_delegate = device_delegate
		self.device_delegate.factory = self
		# for internal usage
		self.timestamp = None
		self.registered = False
		self.states_stack = []
		self.registration_finished = Deferred()

	def doStart(self) :
		if self.state.value == ProtocolState.Unknown :
			self.state = StateHolder(ProtocolState.Register)
		BaseHTTP11ClientFactory.doStart(self)

	def buildProtocol(self, addr):
		return HTTP11DeviceHiveProtocol(self)

	def handleConnectionLost(self, connector):
		def reconnect(connector) :
			connector.connect()
		if (not BaseHTTP11ClientFactory.handleConnectionLost(self, connector)) and (not self.oneshot) and (self.registered):
			# Because Registration is a very first thing which is invoked I do not
			# need to add an addition verification here
			if len(self.states_stack) > 0 :
				tmp_state = self.states_stack.pop(0)
				# If user made a bunch of notifications before device got registered
				# we send them all here at one go
				while tmp_state.value == ProtocolState.Notify :
					self.single_request(tmp_state)
					tmp_state = None
					if len(self.states_stack) > 0:
						tmp_state = self.states_stack.pop(0)
					else :
						return
				# In current implementation this could be only ProtocolState.Command
				if tmp_state is not None :
					self.state = tmp_state
					reactor.callLater(self.poll_interval, reconnect, connector)
				#
		# end

	def next_state(self, next_state, data = None, connector = None) :
		if self.registered and (next_state == ProtocolState.Notify or next_state == ProtocolState.Report) :
			self.single_request(StateHolder(next_state, data))
		else :
			self.states_stack.append(StateHolder(next_state, data, self.retries))
			if (not self.started) and (connector is not None) and (connector.state == 'disconnected') :
				self.handleConnectionLost(connector)

	def single_request(self, state):
		subfactory = _SingleRequestHTTP11DeviceHiveFactory(self, state, self.retries)
		reactor.connectTCP(self.host, self.port, subfactory)

