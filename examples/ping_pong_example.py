#!/usr/bin/env python
# -*- coding: utf8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

import sys
import os
import argparse
from twisted.python import log
from twisted.internet import reactor, task
from zope.interface import implements

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime
from time import time

import devicehive
import devicehive.auto
import devicehive.poll
import devicehive.gateway
import devicehive.gateway.binary

import devicehive.client.ws
import devicehive.interfaces

from serial import PARITY_NONE
from serial import STOPBITS_ONE
from serial import EIGHTBITS


class PingApp(object):
    
    implements(devicehive.interfaces.IClientApp)
    
    def __init__(self, dev_id):
        self.dev_id = dev_id
        self.on_state = False
        self.tm = 0
    
    def connected(self):
        def on_ok(result):
            print 'The application authenticated.'
            def on_subscribed(msg):
                print 'Application subscribed.'
                self.send_next_command()
            def on_subscribed_failed(rsn):
                print 'Application failed to subscribe.'
            self.factory.subscribe([self.dev_id]).addCallbacks(on_subscribed, on_subscribed_failed)
        def on_fail(reason):
            print 'The application FAILED authentication.'
        self.factory.authenticate('YOUR_LOGIC', 'YOUR_PASSWORD').addCallbacks(on_ok, on_fail)
    
    def do_notification(self, device_id, notification):
        print 'Notification {0} has been received for device {1}.'.format(notification, device_id)
    
    def failure(self, reason):
        print 'Network failure {0}'.format(reason)
    
    def send_next_command(self):
        print 'APP -> DH: {0}'.format(datetime.utcnow())
        def on_cmd_sent(res):
            #print 'DH -> APP: {0}. CMD: {1}.'.format(datetime.utcnow(), res)
            pass
        self.tm = time()
        self.on_state = not self.on_state
        self.factory.command(self.dev_id, devicehive.client.ws.WsCommand(command='set', parameters= 1 if self.on_state else 0)).addCallback(on_cmd_sent)


class Gateway(devicehive.gateway.BaseGateway):
    def __init__(self, url, factory_cls) :
        super(Gateway, self).__init__(url, factory_cls)
        self.ping_app = None
    
    def registration_received(self, device_info):
        print 'Registration received from device.'
        self.ping_app = PingApp(device_info.id)
        transport = devicehive.client.ws.WebSocketFactory(self.ping_app)
        transport.connect('ws://pg.devicehive.com:8010')
        super(Gateway, self).registration_received(device_info)
    
    def notification_received(self, device_info, notification):
        super(Gateway, self).notification_received(device_info, notification)
    
    def do_command(self, sender, command, finish_deferred):
        print 'DH -> DEVICE: {0}. CMD: {1}'.format(datetime.utcnow(), command)
        print 'Time %0.10f' % (time() - self.ping_app.tm)
        print '--------------------------------------'
        super(Gateway, self).do_command(sender, command, finish_deferred)
        self.ping_app.send_next_command()
    
    def run(self, transport_endpoint, device_factory):
        super(Gateway, self).run(transport_endpoint, device_factory)


def main(sport, brate):
    #log.startLogging(sys.stderr)
    gateway = Gateway('http://pg.devicehive.com/api/', devicehive.poll.PollFactory) # devicehive.auto.AutoFactory)
    # create endpoint and factory to be used to organize communication channel to device
    endpoint = devicehive.gateway.binary.SerialPortEndpoint(reactor, \
                                                            sport, \
                                                            baudrate = brate, \
                                                            bytesize = EIGHTBITS, \
                                                            parity = PARITY_NONE, \
                                                            stopbits = STOPBITS_ONE)
    bin_factory = devicehive.gateway.binary.BinaryFactory(gateway)
    # run gateway application
    gateway.run(endpoint, bin_factory)
    reactor.run()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--serial', type=str, default='/dev/tty.usbmodem1411', dest='sport', required=False, help='serial port')
    parser.add_argument('-b', '--baud', type=int, default=115200, dest='brate', required=False, help='baud rate')
    r = parser.parse_args()
    main(r.sport, r.brate)

