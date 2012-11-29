#!/usr/bin/env python

import sys
import signal
import functools
from os import path
from ConfigParser import ConfigParser as Conf
from twisted.python import log
from twisted.internet import reactor
import devicehive


class VirtualLedInfos(object):
	"""
	Use duck typing to describe virtual device insterd of
	overriding methods in L{DeviceDelegate} subclass.
	"""
	def __init__(self, config):
		"""
		All device description is contained in configuration file and
		an instance of ConfigParser is used to read it.
		"""
		self.config = config
	def device_id(self):
		return self.config.get('device', 'id')
	def device_key(self):
		return self.config.get('device', 'key')
	def device_name(self):
		return self.config.get('device', 'name')
	def device_status(self):
		return 'Online'
	def network_name(self):
		return self.config.get('network', 'name')
	def network_description(self):
		return self.config.get('network', 'description')
	def device_class_name(self):
		return self.config.get('device_class', 'name')
	def device_class_version(self):
		return self.config.get('device_class', 'version')
	def device_class_is_permanent(self):
		return False
	def equipment(self):
		return [devicehive.Equipment(name = 'VirtualLED', code = 'LED', _type = 'Controllable LED'),]


class VirtualLedDelegate(VirtualLedInfos, devicehive.DeviceDelegate):
	"""
	A subclass of DeviceDelegate class.
	"""
	def __init__(self, config):
		super(VirtualLedDelegate, self).__init__(config)
		self._led_state = 0

	def status_notify(self):
		self.notify('equipment', equipment = 'LED', state = self._led_state)

	def do_update_led_state(self, finish_deferred, equipment = None, state = 0):
		if equipment == 'LED':
			self._led_state = state
			self.status_notify()
			finish_deferred.callback(devicehive.CommandResult('Completed'))
		else :
			finish_deferred.errback(NotImplementedError('Unknown equipment {0}.'.format(equipment)))

	def do_command(self, command, finish_deferred):
		if command['command'] == 'UpdateLedState':
			params = command['parameters']
			self.do_update_led_state(finish_deferred, **params)
		else :
			finish_deferred.errback(NotImplementedError('Unknown command {0}.'.format(command['command'])))


def initialize_logging():
	"""
	Initialize logging. Logs will be printed into standard output
	"""
	log.startLogging(sys.stdout)


def signal_handler(signum, e, dev=None):
	log.msg("Terminating reactor.")
	reactor.stop()


def init_signal_handlers(dev):
	sig_func = functools.partial(signal_handler, dev = dev)
	if hasattr(signal, "SIGTERM"):
		signal.signal(signal.SIGTERM, sig_func)
	if hasattr(signal, "SIGINT"):
		signal.signal(signal.SIGINT, sig_func)
	if hasattr(signal, "SIGHUP"):
		signal.signal(signal.SIGHUP, sig_func)


if __name__ == '__main__':
	initialize_logging()
	# read conf-file
	conf = Conf()
	conf.read(path.join(path.dirname(__file__), path.splitext(path.basename(__file__))[0] + ".cfg"))
	# create device-delegate instance
	virt_led = VirtualLedDelegate(conf)
	# install signal handlers
	init_signal_handlers(virt_led)
	# Default factory for HTTP11 protocol
	virt_led_factory = devicehive.HTTP11DeviceHiveFactory(device_delegate = virt_led)
	# Send notification right after registration
	virt_led.status_notify()
	# Connect to device-hive
	reactor.connectDeviceHive("http://pg.devicehive.com/api/", virt_led_factory)
	try :
		reactor.run()
	except KeyboardInterrupt, err:
		reactor.stop()
