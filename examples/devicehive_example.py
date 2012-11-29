#/usr/bin/env python

import sys
import time
import uuid
from twisted.python import log
from twisted.internet import reactor, task
import devicehive


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
		# end do_command

	def run_me(self):
		print('do something')


i = 0
def looping_call(dev):
	global i
	print ('Sending looping notification {0}.'.format(i))
	dev.notify('looping_notification', count = i, one_more_parameter = 'parameter_value')
	i += 1


def init_logging():
	log.startLogging(sys.stdout)


if __name__ == '__main__' :
	init_logging()
	#
	device = LEDHiveDelegate()
	led_factory = devicehive.HTTP11DeviceHiveFactory(device_delegate = device)
	reactor.connectDeviceHive("http://pg.devicehive.com/api/", led_factory)
	reactor.callWhenRunning(device.run_me)
	lc = task.LoopingCall(looping_call, device)
	lc.start(10)
	reactor.run()
