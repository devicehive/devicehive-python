#!/usr/bin/env python
# -*- encoding: utf8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8 encoding=utf-8

import sys
import signal
from twisted.python import log
from twisted.internet import reactor
import devicehive
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


def stop_handler(signum, e):
    log.msg('Signal trapped. Terminating application. Stopping reactor.')
    reactor.stop()


def install_signal_handlers():
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, stop_handler)
    if hasattr(signal, 'SIGINT'):
        signal.signal(signal.SIGINT, stop_handler)
    if hasattr(signal, 'SIGHUP'):
        signal.signal(signal.SIGHUP, stop_handler)


def main():
    log.startLogging(sys.stdout)
    install_signal_handlers()
    gateway = Gateway('http://pg.devicehive.com/api/', devicehive.HTTP11DeviceHiveFactory)
    # create endpoint and factory to be used to organize communication channel to device
    endpoint = devicehive.gateway.binary.SerialPortEndpoint(reactor, \
                                                            'COM2', \
                                                            baudrate = 9600, \
                                                            bytesize = EIGHTBITS, \
                                                            parity = PARITY_NONE, \
                                                            stopbits = STOPBITS_ONE)
    bin_factory = devicehive.gateway.binary.BinaryFactory(gateway)
    # run gateway application
    gateway.run(endpoint, bin_factory)
    reactor.run()


if __name__ == '__main__':
    main()


