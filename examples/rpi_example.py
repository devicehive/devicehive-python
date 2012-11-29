#!/usr/bin/env python 
# rpi example

import sys
import signal
import functools
from os import path
from ConfigParser import ConfigParser
from time import sleep

try:
	import RPi.GPIO as GPIO
except ImportError:
	class FakeGPIO(object):
		OUT = 'OUTPUT BCM.GPIO17'
		def __init__(self):
			print 'Fake gpio initialized'
		def setup(self, io, mode):
			print 'Set gpio {0}; Mode: {1};'.format(io, mode)
		def output(self, io, vlaue):
			print 'Set gpio {0}; Value: {1};'.format(io, vlaue)
	GPIO = FakeGPIO()
import threading, datetime, logging, sys
from twisted.python import log
from twisted.internet import reactor
import devicehive


_W1_FILENAME = '/sys/bus/w1/devices/28-00000393268a/w1_slave'
_LED_PIN     = 11


class RPiDescr(object):
	"""
	RPi description
	"""
	def __init__(self):
		self._device_id = ''
		self._device_key = ''
	def device_id(self):
		return self._device_id
	def device_key(self):
		return self._device_key
	def device_name(self):
		return 'RPi/Py LED Device'
	def device_status(self):
		return 'Online'
	def network_name(self):
		return 'Python Network'
	def network_description(self):
		return 'Python Devices Test Network'
	def device_class_name(self):
		return 'Python Device Class'
	def device_class_version(self):
		return '1.0'
	def device_class_is_permanent(self):
		return False
	def equipment(self):
		return [devicehive.Equipment(name = 'LED', code = 'LED', _type = 'Controllable LED'),
		        devicehive.Equipment(name = 'DS18B20', code = 'temp', _type = 'Temperature Sensor')]


class RPiDelegate(RPiDescr, devicehive.DeviceDelegate):
	def __init__(self):
		super(RPiDelegate, self).__init__()
		self._last_temperature = None

	def initialize(self, config_file_path):
		self.init_config(config_file_path)
		self.init_gpio()

	def init_config(self, config_file_path):
		conf = ConfigParser()
		conf.read(config_file_path)
		self._device_id = conf.get('device', 'id')
		self._device_key = conf.get('device', 'key')

	def init_gpio(self):
		GPIO.setup(_LED_PIN, GPIO.OUT) # BCM.GPIO17
		for i in range(5):
			GPIO.output(_LED_PIN, True)
			sleep(0.2)
			GPIO.output(_LED_PIN, False)
			sleep(0.2)

	def on_registration_finished(self, value):
		"""
		Send temperature update right after device
		has registered in device-hive server.
		"""
		self.update_temperature()

	def update_temperature(self):
		try :
			temperature = self.read_temperature(_W1_FILENAME)
			if self.need_to_notify(temperature):
				self._last_temperature = temperature
				self.notify('equipment', equipment = 'temp', temperature = temperature)
		except Exception, err :
			print 'Failed to read temperature file. Got error <{0}>.'.format(err)
		reactor.callLater(1.0, self.update_temperature)

	def need_to_notify(self, temperature):
		if self._last_temperature == None:
			return True
		return abs(temperature - self._last_temperature) > 0.2

	def read_temperature(self, file_name):
		with open(file_name) as f:
			content = f.readlines()
			for line in content:
				if line.find('crc=') >= 0 and line.find('NO') >= 0:
					return self.last_temp
				p = line.find('t=')
				if p >= 0:
					return float(line[p+2:]) / 1000.0
		pass

	def do_command(self, command, finish_deferred):
		cmd_name = command['command']
		cmd_params = command['parameters']
		if cmd_name == 'UpdateLedState':
			equipment = cmd_params['equipment']
			state = cmd_params['state']
			log.msg("<{0}> -> {1}.".format(equipment, state))
			GPIO.output(_LED_PIN, int(state, 10))
			finish_deferred.calback(devicehive.CommandResult('Completed', 'OK'))
		else:
			finish_deferred.errback(NotImplementedError('Unknown command: <{0}> ignored.'.format(cmd_name)))


def initialize_logging():
	"""
	Initialize logging. Logs will be printed into standard output
	"""
	log.startLogging(sys.stdout)


def init_signal_handlers():
	def signal_handler(signum, e):
		log.msg("Terminating reactor.")
		reactor.stop()
	if hasattr(signal, "SIGTERM"):
		signal.signal(signal.SIGTERM, signal_handler)
	if hasattr(signal, "SIGINT"):
		signal.signal(signal.SIGINT, signal_handler)
	if hasattr(signal, "SIGHUP"):
		signal.signal(signal.SIGHUP, signal_handler)


def config_file_name():
	return path.join(path.dirname(__file__), path.splitext(path.basename(__file__))[0] + ".cfg")


def on_registered(response, device = None):
	print 'Registration finished. Running temperature read-update loop for <{0}> device.'.format(device)
	device.on_registration_finished(response)


if __name__ == '__main__' :
	# 0.
	initialize_logging()
	init_signal_handlers()
	# 1.
	rpi_dev = RPiDelegate()
	rpi_dev.initialize(config_file_name())
	# 2.
	factory = devicehive.HTTP11DeviceHiveFactory(device_delegate = rpi_dev)
	factory.registration_finished.addCallback(functools.partial(on_registered, device = rpi_dev))
	# 3.
	reactor.connectDeviceHive("http://pg.devicehive.com/api/", factory)
	reactor.run()
