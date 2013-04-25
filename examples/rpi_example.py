#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:
#
# Raspberry Pi example
#

import sys
import os
import threading
from ConfigParser import ConfigParser
from time import sleep

from twisted.python import log
from twisted.internet import reactor
from zope.interface import implements

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

try:
    import devicehive
except :
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import devicehive
import devicehive.interfaces
import devicehive.auto


W1_FILENAME = '/sys/bus/w1/devices/28-00000393268a/w1_slave'
LED_PIN     = 11


class RPiDescr( devicehive.DeviceInfo ):
    """
    This class describe a raspberry pi virtual device.
    """
    
    implements(devicehive.IDeviceInfo)
    
    def __init__(self):
        super(RPiDescr, self).__init__(name = 'RPi/Py LED Device',
                                       status = 'Online',
                                       network = devicehive.Network(key = 'Python Network',
                                                                    name = 'Python Network',
                                                                    descr = 'Python Devices Test Network'),
                                       device_class = devicehive.DeviceClass(name = 'Python Device Class',
                                                                             version = '1.0'),
                                       equipment = [devicehive.Equipment(name = 'LED', code = 'LED', type = 'Controllable LED'),
                                                    devicehive.Equipment(name = 'DS18B20', code = 'temp', type = 'Temperature Sensor')])
        pass


class BaseRPiApp(object):
    
    implements(devicehive.interfaces.IProtoHandler)
    
    factory = None
    
    info = RPiDescr()
    
    def on_apimeta(self, websocket_server, server_time):
        pass
    
    def on_connected(self):
        pass
    
    def on_connection_failed(self, reason) :
        pass
    
    def on_closing_connection(self):
        pass
    
    def on_failure(self, device_id, reason):
        pass
    
    def on_command(self, device_id, command, finished):
        raise NotImplementedError('You need to override base abstract method.')
    
    def notify(self, notification, **params):
        if self.factory is not None :
            self.factory.notify(notification, params, self.info.id, self.info.key)


class RPiApp(BaseRPiApp) :
    def __init__(self):
        super(RPiApp, self).__init__()
        self.last_temperature = None
    
    def initialize(self, config_file_path):
        self.init_config(config_file_path)
        self.init_gpio()
    
    def init_config(self, config_file_path):
        conf = ConfigParser()
        conf.read(config_file_path)
        self.info.id = conf.get('device', 'id')
        self.info.key = conf.get('device', 'key')
    
    def init_gpio(self):
        GPIO.setup(LED_PIN, GPIO.OUT) # BCM.GPIO17
        for i in range(5):
            GPIO.output(LED_PIN, True)
            sleep(0.2)
            GPIO.output(LED_PIN, False)
            sleep(0.2)
    
    def on_connected(self):
        """
        Register one or more devices right after library
        has connected todevice-hive server.
        """
        def on_subscribe(result) :
            """
            After device has registered in device-hive server it
            sends temperature update notification. And then it starts listening for a command.
            """
            self.update_temperature()
            self.factory.subscribe(self.info.id, self.info.key)
        def on_failed(reason) :
            log.err('Failed to save device {0}. Reason: {1}.'.format(self.info, reason))
        self.factory.device_save(self.info).addCallbacks(on_subscribe, on_failed)
    
    def update_temperature(self):
        try :
            temperature = self.read_temperature(W1_FILENAME)
            if self.need_to_notify(temperature):
                self.last_temperature = temperature
                self.notify('equipment', equipment = 'temp', temperature = temperature)
        except Exception, err :
            log.err('Failed to read temperature file. Got error <{0}>.'.format(err))
        reactor.callLater(1.0, self.update_temperature)
    
    def need_to_notify(self, temperature):
        if self.last_temperature is None :
            return True
        return abs(temperature - self.last_temperature) > 0.2
    
    def read_temperature(self, file_name):
        with open(file_name) as f :
            content = f.readlines()
            for line in content :
                if line.find('crc=') >= 0 and line.find('NO') >= 0 :
                    return self.last_temp
                p = line.find('t=')
                if p >= 0:
                    return float(line[p+2:]) / 1000.0
    
    def on_command(self, device_id, command, finished):
        cmd_name = command.command
        cmd_params = command.parameters
        if cmd_name == 'UpdateLedState' :
            equipment = cmd_params['equipment']
            state = cmd_params['state']
            log.msg("<{0}> -> {1}.".format(equipment, state))
            GPIO.output(LED_PIN, int(state, 10))
            finished.calback(devicehive.CommandResult('Completed', 'OK'))
        else :
            finished.errback(NotImplementedError('Unknown command: <{0}> ignored.'.format(cmd_name)))


def config_file_name():
    return os.path.join(os.path.dirname(__file__), os.path.splitext(os.path.basename(__file__))[0] + '.cfg')


if __name__ == '__main__' :
    # 0.
    log.startLogging(sys.stdout)
    # 1.
    rpi_app = RPiApp()
    rpi_app.initialize(config_file_name())
    # 2.
    factory = devicehive.auto.AutoFactory(rpi_app)
    # 3.
    factory.connect("http://pg.devicehive.com/api/")
    reactor.run()

