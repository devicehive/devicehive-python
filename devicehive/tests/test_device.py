# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8 encoding=utf-8:

import sys
from os import path
from twisted.python import log
from twisted.internet import reactor, task
from zope.interface import implements

sys.path.insert(0, path.abspath(path.join(path.dirname(__file__), '..', '..')))
import devicehive
import devicehive.poll
import devicehive.interfaces



class LogicHandler(object):
    """
    Abstract implementation of IProtoHandler. Handles only one device.
    """
    
    implements(devicehive.interfaces.IProtoHandler)
    
    def __init__(self):
        self.factory = None

    def test_factory(self):
        return IProtoFactory.implementedBy(self.factory.__class__)
    
    def on_failure(self, reason):
        pass
    
    def on_apimeta(self, websocket_server, server_time):
        log.msg('API Info retrieved.')
    
    def on_connected(self):
        info = self.device_info()
        def do_subscribe() :
            self.factory.subscribe(info.id, info.key)
        self.factory.device_save(info).addCallback(do_subscribe)
    
    def on_closing_connection(self):
        pass
    
    def on_command(self, deviceguid, command, finished):
        raise NotImplementedError()
    
    def device_info(self):
        """
        Method returns a list of object each of which has to
        implement C{devicehive.interfaces.IDeviceInfo} interface.
        """
        net = devicehive.Network(id = '1', key = 'network11', name = 'Network 1.1', descr = 'Network version 1.1')
        dec = devicehive.DeviceClass(name = 'Example Device Class', version = 'Example Device Class 1.1')
        eqp = [devicehive.Equipment(name = 'Example Equipment', code = 'EXEQCO', type = 'ExampleType11'), ]
        di1 = devicehive.DeviceInfo(id = '0204eede-2297-11e2-882c-e0cb4eb92129',
                                   key = 'Exmaple Device 1 Key',
                                   name = 'DeviceHive Python Example 1',
                                   network = net,
                                   device_class = dec,
                                   equipment = eqp)
        di2 = devicehive.DeviceInfo(id = '0304eede-2297-11e2-882c-e0cb4eb92129',
                                   key = 'Exmaple Device 2 Key',
                                   name = 'DeviceHive Python Example 2',
                                   network = net,
                                   device_class = dec,
                                   equipment = eqp)
        return (di1, di2)
    
    def on_connected(self):
        for info in self.device_info() :
            self.connect_device(info)
    
    def connect_device(self, info):
        def on_subscribe(result) :
            self.factory.subscribe(info.id, info.key)
        def on_failed(reason) :
            log.err('Failed to save device {0}. Reason: {1}.'.format(info, reason))
        self.factory.device_save(info).addCallbacks(on_subscribe, on_failed)
    
    def on_command(self, deviceguid, command, finished):
        finished.errback(NotImplementedError())


def main():
    log.startLogging(sys.stdout)
    handler = LogicHandler()
    factory = devicehive.poll.PollFactory(handler)
    reactor.connectDeviceHive('http://ecloud.dataart.com/ecapi7/', factory)
    reactor.run()


if __name__ == '__main__' :
    main()

