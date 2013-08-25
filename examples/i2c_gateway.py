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
import devicehive.gateway
import devicehive.gateway.i2c


DEVICE_INFO = ((0x78,
               devicehive.DeviceInfo(id=str('1d197265-2272-493a-b4c4-a79387111a57'),
                                     name='Echo',
                                     key='0x78',
                                     network=devicehive.Network(id='i2cnet', key='i2cnet', name='I2C network'),
                                     device_class=devicehive.DeviceClass(name='echo',
                                                                         version='0.1'),
                                     equipment=[devicehive.Equipment(name='i2c-echo',
                                                                     code='i2c-echo',
                                                                     type='i2c-echo')])),
               (0x1e,
               devicehive.DeviceInfo(id=str('19c7ef2a-ee97-4ed2-be49-7fc7a6d6e85d'),
                                     key='0x3c',
                                     name='Compass',
                                     network=devicehive.Network(id='i2cnet', key='i2cnet', name='I2C network'),
                                     device_class=devicehive.DeviceClass(name='compass',
                                                                         version='0.1'),
                                     equipment=[devicehive.Equipment(name='compass',
                                                                     code='compass',
                                                                     type='compass')])),
               (0x68,
               devicehive.DeviceInfo(id=str('a10467f9-1d0f-44b0-b3c7-604d84ac254d'),
                                     key='0x68',
                                     name='Gyro',
                                     network=devicehive.Network(id='i2cnet', key='i2cnet', name='I2C network'),
                                     device_class=devicehive.DeviceClass(name='Gyro',
                                                                         version='0.01'),
                                     equipment=[devicehive.Equipment(name='gyroscope',
                                                                     code='ITG3200',
                                                                     type='gyroscope')]))
)

class I2cGateway(devicehive.gateway.BaseGateway):
    def __init__(self, url, factory_cls):
        super(I2cGateway, self).__init__(url, factory_cls)

    def registration_received(self, device_info):
        super(I2cGateway, self).registration_received(device_info)

    def notification_received(self, device_info, notification):
        super(I2cGateway, self).notification_received(device_info, notification)

    def do_command(self, sender, command, finish_deferred):
        super(I2cGateway, self).do_command(sender, command, finish_deferred)

    def run(self, transport_endpoint, device_factory):
        super(I2cGateway, self).run(transport_endpoint, device_factory)


def main(adaptor):
    log.startLogging(sys.stdout)
    # gateway = I2cGateway('http://pg.devicehive.com/api/', devicehive.auto.AutoFactory)
    gateway = I2cGateway('http://ecloud.dataart.com/ecapi8', devicehive.auto.AutoFactory)
    endpoint = devicehive.gateway.i2c.I2cEndpoint(reactor, adaptor, DEVICE_INFO)
    factory = devicehive.gateway.i2c.I2cProtoFactory(gateway)
    # run gateway application
    gateway.run(endpoint, factory)
    reactor.run()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--adaptor', type=int,
                        default=1,
                        dest='adaptor',
                        required=False,
                        help='i2c adaptor')
    r = parser.parse_args()
    main(r.adaptor)
