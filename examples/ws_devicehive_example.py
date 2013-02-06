#/usr/bin/env python

import sys
import time
import uuid
from twisted.python import log
from twisted.internet import reactor, task


import sys
from os import path

orig_path = list(sys.path)
sys.path.insert(0, path.abspath(path.join(path.dirname(__file__), '..')))
try :
    devicehive = __import__('devicehive')
finally :
    sys.path[:] = orig_path


def threading_command(finish_defer) :
	print('Thread command handling started.')
	time.sleep(5)
	print('Thread command handling finished.')
	def not_thread_safe(d):
		print('Call defer callback from main thread')
		d.callback('Completed')
	reactor.callFromThread(not_thread_safe, finish_defer)


class LEDHiveDelegate(devicehive.DeviceDelegate):
	def device_id(self):
		return '0204eede-2297-11e2-882c-e0cb4eb92129'

	def device_key(self):
		return 'Exmaple Device Key'

	def device_name(self):
		return 'DeviceHive Python Example'

	def device_status(self):
		return 'Online'

	def network_name(self):
		return 'Network Name'

	def network_description(self):
		return 'Network Description'

	def device_class_name(self):
		return 'Example Network'

	def device_class_version(self):
		return '1.0'

	def device_class_is_permanent(self):
		return False

	def equipment(self):
		return [devicehive.Equipment(name = 'ExampleEquipment', code = 'ExampleCode', _type = 'ExampleType'), ]

	def do_short_command(self, finish_deferred):
		finish_deferred.callback(devicehive.CommandResult('Completed'))

	def do_long_async_command(self, finish_deferred, echo_str):
		def command_finished(finish_d, par_echo_string) :
			print 'Device async acomplished.'
			finish_d.callback(devicehive.CommandResult('Completed', par_echo_string))
		reactor.callLater(10, command_finished, finish_deferred, echo_str)

	def do_long_thread_command(self, finish_deferred):
		print('Starting command handling thread')
		# or regular (threading.Thread(threading_command,...)).start()
		reactor.callInThread(threading_command, finish_defer =finish_deferred)

	def do_command(self, command, finish_deferred):
		print 'do_command handle'
		if command['command'] == 'short' :
			print 'short command handle'
			self.do_short_command(finish_deferred)
		elif command['command'] == 'long_async' :
			self.do_long_async_command(finish_deferred, command['parameters']['echo_str'])
		elif command['command'] == 'long_thread' :
			self.do_long_thread_command(finish_deferred)
		else :
			finish_deferred.errback(NotImplementedError('Command is not supported.'))


if __name__ == '__main__' :
    log.startLogging(sys.stdout)
    #
    device = LEDHiveDelegate()
    factory = devicehive.WebSocketDeviceHiveFactory(device_delegate = device)
    reactor.connectDeviceHive('http://ecloud.dataart.com/ecapi7', factory)
    reactor.run()

