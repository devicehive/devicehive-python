#!/usr/bin/env python
# -*- encoding: utf-8 -*-

# @author astaff
#
# This sample is to demonstrate DeviceHive Python library
# Connect LED to PIN11 of the board and 1-wire sensor to GPIO4 board PIN #7,
# use pins #1 (3v3) or #2 (5v) for power and pin #6 for ground
#
# (C) DataArt Apps, 2012
# Distributed under MIT license
#

import sys
import os
import time
from time import sleep

from zope.interface import implements
from twisted.python import log
from twisted.internet import reactor, task

import devicehive
import devicehive.auto


# analog pin
ADC_PIN = 37
ADC_DEV = 0
ADC_CH = 0

# Board's pin #11 (GPIO17)
_LED_PIN = 27

# API URL (register for free playground at http://beta2.devicehive.com/playground
_API_URL = 'http://pg.devicehive.com/api/'


class SysFsGPIO(object):
    BOARD = None
    OUT = 'out'
    IN = 'in'

    def __init__(self, sysfs_path):
        self.sysfs_path = sysfs_path
        self.exported_pins = set()

    def setmode(self, mode):
        pass

    def __ensure_pin_exported(self, io):
        if not os.path.exists('%s/gpio%d' % (self.sysfs_path, io)):
            with open('%s/export' % self.sysfs_path, 'w') as f:
                f.write(str(io))
            self.exported_pins.add(io)

    def setup(self, io, mode):
        self.__ensure_pin_exported(io)
        with open('%s/gpio%d/direction' % (self.sysfs_path, io), 'w') as f:
            f.write(mode)
        with open('%s/gpio%d/drive' % (self.sysfs_path, io), 'w') as f:
            f.write('strong')

    def output(self, io, value):
        with open('%s/gpio%d/value' % (self.sysfs_path, io), 'w') as f:
            f.write('1' if value else '0')

    def __del__(self):
        for io in self.exported_pins:
            with open('%s/unexport' % self.sysfs_path) as f:
                f.write(str(io))


GPIO = SysFsGPIO('/sys/class/gpio')

#
# for easier reading, this class holds all registration information for DeviceHive
#
class RasPiConfig(object):
    
    implements(devicehive.interfaces.IDeviceInfo)
    
    @property
    def id(self):
        return '9f33566e-1f8f-11e2-8979-c42c030dd6a5'
    
    @property
    def key(self):
        return 'device-key'
    
    @property
    def name(self):
        return 'Device1'
    
    @property
    def status(self):
        return 'Online'
    
    @property
    def network(self):
        return devicehive.Network(key = 'Netname', name = 'Netname', descr = 'RasPi/Py LED/w1 sample')
    
    @property
    def device_class(self):
        return devicehive.DeviceClass(name = 'Class1', version = '1.0', is_permanent = False)
    
    @property
    def equipment(self):
        return [devicehive.Equipment(name = 'LED', code = 'LED', type = 'Controllable LED'), devicehive.Equipment(name = 'THERMO', code = 'temp', type = 'TempSensor')]

#
# This class handles DeviceHive API calls for our device
#
class RasPiApp(object):
    
    implements(devicehive.interfaces.IProtoHandler)
    
    def __init__(self, led, sensor):
        super(RasPiApp, self).__init__()
        self.connected = False
        self.notifs = []
        self.info = RasPiConfig()
        self.led = led
        self.sensor = sensor
    
    def on_apimeta(self, websocket_server, server_time):
        log.msg('on_apimeta')
    
    def on_connected(self):
        lc = task.LoopingCall(self.sensor.get_temp, self)
        lc.start(1)
        
        log.msg('Connected to devicehive server.')
        self.connected = True
        for onotif in self.notifs :
            self.factory.notify(onotif['notification'], onotif['parameters'], device_id = self.info.id, device_key = self.info.key)
        self.notifs = []
        def on_subscribe(result) :
            self.factory.subscribe(self.info.id, self.info.key)
        def on_failed(reason) :
            log.err('Failed to save device {0}. Reason: {1}.'.format(self.info, reason))
        self.factory.device_save(self.info).addCallbacks(on_subscribe, on_failed)
    
    def on_connection_failed(self, reason) :
        pass
    
    def on_closing_connection(self):
        pass
    
    def on_failure(self, device_id, reason):
        pass
    
    def do_short_command(self, finished, equipment = None, state = 0):
        log.msg('Setting {0} equipment to {1}'.format(equipment, state))
        if equipment == 'LED' :
            if int(state) == 0 :
                self.led.set_off()
            else:
                self.led.set_on()
        # upon completion post the result back
        self.factory.notify('equipment', {'state': state, 'equipment': 'LED'}, device_id = self.info.id, device_key = self.info.key)
        finished.callback(devicehive.CommandResult('Completed'))
    
    def on_command(self, device_id, command, finished):
        # Expecting command as 'UpdateState' and parameters as {"equipment" : "LED", "state" : "0"}
        if command.command == 'UpdateLedState' :
            self.do_short_command(finished,  **command.parameters)
        else :
            finished.errback()
        # end do_command
    
    def notify(self, notif, **params):
        if self.connected :
            self.factory.notify(notif, params, device_id = self.info.id, device_key = self.info.key)
        else :
            self.notifs.append({'notification': notif, 'parameters': params})


class TempSensor(object):
    GPIO_PATH = '/sys/class/gpio'
    ADC_PATH = '/sys/bus/iio/devices/iio:device%d/in_voltage%d_raw'

    def __init__(self, pin, device, channel):
        self.pin = pin
        self.device = device
        self.channel = channel

        self.last_temp = 0
        self.last_good_temp = 0

        if not os.path.exists('%s/gpio%d/value' % (self.GPIO_PATH, self.pin)):
            with open('%s/export' % self.GPIO_PATH, 'w') as f:
                f.write(str(self.pin))
        with open('%s/gpio%d/direction' % (self.GPIO_PATH, self.pin), 'w') as f:
            f.write(GPIO.OUT)
        with open('%s/gpio%d/value' % (self.GPIO_PATH, self.pin), 'w') as f:
            f.write('0')

    def _get_temp(self):
        try:
            with open(self.ADC_PATH % (self.device, self.channel), 'r') as f:
                data = f.read()
                if data:
                    volts = (5000 * int(data)) / 4096
                    return (volts - 500) / 10.0
                return 0.0
        except Exception as e:
            print 'Failed to convert temperature. Reason: %s' % e
            return 0.0

    # check temperature, if greater than threshold, notify
    def get_temp(self, dev):
        temp = self._get_temp()
        if abs(temp - self.last_temp) > 0.2:
            log.msg('Temperature {0} -> {1}'.format(self.last_temp, temp))
            dev.notify('equipment', temperature = temp, equipment = "temp")
            self.last_temp = temp


#
# Wrapper from LED connected to RasPi
#
class LedDevice(object):
    def __init__(self, pin):
        # We are using board PIN numbering (as opposed to chip's numbers)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(pin, GPIO.OUT)

    def blink(self, count):
        for i in range(count):
            GPIO.output(_LED_PIN, True)
            sleep(0.2)
            GPIO.output(_LED_PIN, False)
            sleep(0.2)

    def set_on(self):
        GPIO.output(_LED_PIN, True)

    def set_off(self):
        GPIO.output(_LED_PIN, False)

#
# main
#
if __name__ == '__main__' :
    log.startLogging(sys.stdout)
    
    led = LedDevice(_LED_PIN)
    # Blink on start to ensure device is working
    led.blink(3)

    # create temp sensor and queue it to check for temperature in a separate thread
    tempSensor = TempSensor(ADC_PIN, ADC_DEV, ADC_CH)
    
    # create a delegate to handle commands
    device = RasPiApp(led, tempSensor)
    led_factory = devicehive.auto.AutoFactory(device)
    led_factory.connect(_API_URL)   
    
    # off we go!
    reactor.run()

