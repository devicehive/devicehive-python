#/usr/bin/env python

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
import time

import RPi.GPIO as GPIO
import devicehive

from time import sleep
from twisted.python import log
from twisted.internet import reactor, task

# change it to match your address for 1-wire sensor
_W1_FILENAME='/sys/bus/w1/devices/28-00000393268a/w1_slave'
# Board's pin #11 (GPIO17)
_LED_PIN=11
# API URL (register for free playground at http://beta2.devicehive.com/playground
_API_URL = 'http://nn57.pg.devicehive.com/api'


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
    
    def __init__(self, led):
        super(RasPiApp, self).__init__()
        self.connected = False
        self.notifs = []
        self.info = RasPiConfig()
        self.led = led
    
    def on_apimeta(self, websocket_server, server_time):
        pass
    
    def on_connected(self):
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
            self.factory(notif, params, device_id = self.info.id, device_key = self.info.key)
        else :
            self.notifs.append({'notification': notif, 'parameters': params})


#
# Temperature sensor wrapper. Gets temperature readings form file, parses them
# and notifies the services is the difference is greater than a certain threshold
#
class TempSensor(object):
    def __init__(self, file_name):
        self.file_name = file_name
        self.last_temp = 0
        self.last_good_temp = 0
        pass

    # internal, get temperature readings from device and check CRC
    def _get_temp(self):
        with open(self.file_name) as f:
            content = f.readlines()
            for line in content:
                # sometimes CRC is bad, so we will return last known good temp
                if line.find('crc=')>=0 and line.find('NO')>=0:
                    return self.last_good_temp
                p = line.find('t=')
                if p >= 0:
                    self.last_good_temp = float(line[p+2:])/1000.0
                    return self.last_good_temp
        pass

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
            GPIO.output(_LED_PIN,True)
            sleep(0.2)
            GPIO.output(_LED_PIN,False)
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
    
    # create a delegate to handle commands
    device = RasPiDelegate(led)
    led_factory = devicehive.auto.AutoFactory(device)
    reactor.connectDeviceHive(_API_URL, led_factory)
    
    # create temp sensor and queue it to check for temperature in a separate thread
    tempSensor = TempSensor(_W1_FILENAME)
    lc = task.LoopingCall(tempSensor.get_temp, device)
    lc.start(1)
    
    # off we go!
    reactor.run()

