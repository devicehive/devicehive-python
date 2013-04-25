#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

import sys
import os
from twisted.python import log
from twisted.internet import reactor
from zope.interface import implements
from ConfigParser import ConfigParser as Conf

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import devicehive
import devicehive.poll
import devicehive.ws
import devicehive.auto
import devicehive.device.ws
import devicehive.interfaces


class VirtualLedInfo(object):
    
    implements(devicehive.interfaces.IDeviceInfo)
    
    def __init__(self, config):
        self.config = config
    
    @property
    def id(self):
        return self.config.get('device', 'id')
    
    @property
    def key(self):
        return self.config.get('device', 'key')
    
    @property
    def name(self):
        return self.config.get('device', 'name')
    
    @property
    def status(self):
        return 'Online'
    
    @property
    def data(self):
        return None
    
    @property
    def network(self):
        return devicehive.Network(key = self.config.get('network', 'name'),
                                  name = self.config.get('network', 'name'),
                                  descr = self.config.get('network', 'description'))
    
    @property
    def device_class(self):
        return devicehive.DeviceClass(name = self.config.get('device_class', 'name'),
                    version = self.config.get('device_class', 'version'))
    
    @property
    def equipment(self):
        return [devicehive.Equipment(name = 'VirtualLED', code = 'LED', type = 'Controllable LED')]
    
    def to_dict(self):
        res = {'key': self.key,
               'name': self.name}
        if self.status is not None :
            res['status'] = self.status
        if self.data is not None :
            res['data'] = data
        if self.network is not None :
            res['network'] = self.network.to_dict() if devicehive.interfaces.INetwork.implementedBy(self.network.__class__) else self.network
        res['deviceClass'] = self.device_class.to_dict() if devicehive.interfaces.IDeviceClass.implementedBy(self.device_class.__class__) else self.device_class
        if self.equipment is not None :
            res['equipment'] = [x.to_dict() for x in self.equipment]
        return res


class VirtualLedApp(object):
    
    implements(devicehive.interfaces.IProtoHandler)
    
    def __init__(self, config):
        self.factory = None
        self.info = VirtualLedInfo(config)
        self.connected = False
        self.led_state = 0
    
    def on_apimeta(self, websocket_server, server_time):
        pass
    
    def on_closing_connection(self):
        pass
    
    def on_connection_failed(self, reason):
        pass
    
    def on_failure(self, device_id, reason):
        pass
    
    def on_connected(self):
        def on_subscribe(result) :
            self.connected = True
            def on_subsc(res):
                print '!!!! SUBSCRIBED'
            self.factory.subscribe(self.info.id, self.info.key).addCallback(on_subsc)
        def on_failed(reason) :
            log.err('Failed to save device {0}. Reason: {1}.'.format(self.info, reason))
        self.factory.device_save(self.info).addCallbacks(on_subscribe, on_failed)
    
    def on_command(self, device_id, command, finished):
        if command.command == 'UpdateLedState':
            self.do_update_led_state(finished, **command.parameters)
        else :
            finished.errback(NotImplementedError('Unknown command {0}.'.format(command.command)))
    
    def do_update_led_state(self, finish_deferred, equipment = None, state = 0):
        if equipment == 'LED':
            self.led_state = state
            self.status_notify()
            finish_deferred.callback(devicehive.CommandResult('Completed'))
        else :
            finish_deferred.errback(NotImplementedError('Unknown equipment {0}.'.format(equipment)))
    
    def status_notify(self):
        if self.connected :
            self.factory.notify('equipment', {'equipment': 'LED', 'state': self.led_state}, self.info.id, self.info.key)


if __name__ == '__main__':
    log.startLogging(sys.stdout)
    # read conf-file
    conf = Conf()
    conf.read(os.path.join(os.path.dirname(__file__), os.path.splitext(os.path.basename(__file__))[0] + '.cfg'))
    # create device-delegate instance
    virt_led = VirtualLedApp(conf)
    # Automacti factory
    # Also it is possible to use C{devicehive.poll.PollFactory} or C{devicehive.ws.WebSocketFactory}
    # virt_led_factory = devicehive.auto.AutoFactory(virt_led)
    #virt_led_factory = devicehive.device.ws.WebSocketFactory(virt_led)
    virt_led_factory = devicehive.poll.PollFactory(virt_led)
    # Send notification right after registration
    virt_led.status_notify()
    # Connect to device-hive
    # virt_led_factory.connect('ws://pg.devicehive.com:8010')
    virt_led_factory.connect('http://pg.devicehive.com/api/')
    reactor.run()
