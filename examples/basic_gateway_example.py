#!/usr/bin/env python
# -*- coding: utf8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

import sys
import os
import argparse
from twisted.python import log
from twisted.internet import reactor

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import devicehive
import devicehive.auto
import devicehive.poll
import devicehive.gateway
import devicehive.gateway.binary
from serial import PARITY_NONE
from serial import STOPBITS_ONE
from serial import EIGHTBITS


class Gateway(devicehive.gateway.BaseGateway):
    def __init__(self, url, factory_cls) :
        super(Gateway, self).__init__(url, factory_cls)
    
    def registration_received(self, device_info):
        super(Gateway, self).registration_received(device_info)
    
    def notification_received(self, device_info, notification):
        super(Gateway, self).notification_received(device_info, notification)
    
    def do_command(self, sender, command, finish_deferred):
        super(Gateway, self).do_command(sender, command, finish_deferred)
    
    def run(self, transport_endpoint, device_factory):
        super(Gateway, self).run(transport_endpoint, device_factory)


def main(sport, brate):
    log.startLogging(sys.stdout)
    gateway = Gateway('http://pg.devicehive.com/api/', devicehive.auto.AutoFactory)
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

