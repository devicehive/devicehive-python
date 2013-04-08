#/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

import sys
import os
import time
from twisted.python import log
from twisted.internet import reactor
from zope.interface import implements
try :
    import devicehive
except :
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import devicehive
import devicehive.interfaces
import devicehive.ws
import devicehive.device.ws


def threading_command(finish_defer) :
	time.sleep(5)
	def not_thread_safe(d):
		d.callback('Completed')
	reactor.callFromThread(not_thread_safe, finish_defer)


class LEDHiveApp(object):
    implements(devicehive.interfaces.IProtoHandler)
    
    def generate_info():
        return devicehive.DeviceInfo(id = '0204eede-2297-11e2-882c-e0cb4eb92129',
                              key = 'Exmaple Device Key',
                              name = 'DeviceHive Python Example',
                              status = 'Online',
                              network = devicehive.Network(key = 'Network Name', name = 'Network Name', descr = 'Network Description'),
                              device_class = devicehive.DeviceClass(name = 'Example Network', version = '1.0', is_permanent = False),
                              equipment = [devicehive.Equipment(name = 'ExampleEquipment', code = 'ExampleCode', type = 'ExampleType')])
    DEVICE_INFO = generate_info()
    
    factory = None
    
    def on_apimeta(self, websocket_server, server_time):
        pass
    
    def on_closing_connection(self):
        pass
    
    def on_connection_failed(self, reason):
        pass
    
    def on_failure(self, device_id, reason):
        log.err('Unhandled error. Device: {0}. Reason: {1}.'.format(device_id, reason))
    
    def on_connected(self):
        def on_subscribe(result) :
            self.factory.subscribe(self.DEVICE_INFO.id, self.DEVICE_INFO.key)
        def on_failed(reason) :
            log.err('Failed to save device {0}. Reason: {1}.'.format(self.DEVICE_INFO, reason))
        self.factory.device_save(self.DEVICE_INFO).addCallbacks(on_subscribe, on_failed)
    
    def do_short_command(self, finished):
        log.msg('short command handle')
        finished.callback(devicehive.CommandResult('Completed'))
    
    def do_long_async_command(self, finished, echo_str):
        def command_finished(finish_d, par_echo_string):
            log.msg('Device async acomplished.')
            finish_d.callback(devicehive.CommandResult('Completed', par_echo_string))
        reactor.callLater(10, command_finished, finished, echo_str)
    
    def do_long_thread_command(self, finished):
        log.msg('Starting command handling thread.')
        reactor.callInThread(threading_command, finish_defer = finished)
    
    def on_command(self, device_id, command, finished):
        if command.command == 'short' :
            self.do_short_command(finished)
        elif command.command == 'long_async' :
            self.do_long_async_command(finished, command.parameters['echo_str'])
        elif command.command == 'long_thread' :
            self.do_long_thread_command(finished)
        else :
            finished.errback(NotImplementedError('Command is not supported.'))


if __name__ == '__main__' :
    log.startLogging(sys.stdout)
    transport = devicehive.device.ws.WebSocketFactory(LEDHiveApp())
    transport.connect('ws://pg.devicehive.com:8010')
    reactor.run()

