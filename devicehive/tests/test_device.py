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
import devicehive.ws
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
        log.msg('API Info. WebSocket server: {0}; server time: {1}.'.format(websocket_server, server_time))
    
    def on_connected(self):
        info = self.device_info()
        def do_subscribe() :
            self.factory.subscribe(info.id, info.key)
        self.factory.device_save(info).addCallback(do_subscribe)
    
    def on_closing_connection(self):
        pass
    
    def on_command(self, deviceguid, command, finished):
        raise NotImplementedError('COMMAND IS NOT IMPLEMENTED')
    
    def device_info(self):
        """
        Method returns a list of object each of which has to
        implement C{devicehive.interfaces.IDeviceInfo} interface.
        """
        net = devicehive.Network(key = 'network11', name = 'network11', descr = 'network11')
        dec = devicehive.DeviceClass(name = 'Example Device Class', version = 'Example Device Class 1.1')
        eqp = [devicehive.Equipment(name = 'Example Equipment', code = 'EXEQCO', type = 'ExampleType11'), ]
        di1 = devicehive.DeviceInfo(id = '22345678-9012-3456-7890-123456789012',
                                   key = 'net11dev1',
                                   name = 'PyExample1',
                                   status = 'Online',
                                   network = net,
                                   device_class = dec,
                                   equipment = eqp)
        di2 = devicehive.DeviceInfo(id = '13456789-0123-4567-8901-234567890123',
                                   key = 'net11dev2',
                                   name = 'PythonExample2',
                                   status = 'Online',
                                   network = net,
                                   device_class = dec,
                                   equipment = eqp)
        return (di1, di2)
    
    def on_connected(self):
        log.msg('On connected')
        for info in self.device_info() :
            self.connect_device(info)
    
    def on_failure(self, device_id, reason):
        """
        @type device_id: C{str}
        @param device_id: device guid
        """
        log.err('Unhandled error. Device: {0}. Reason: {1}.'.format(device_id, reason))
    
    def connect_device(self, info):
        def on_subscribe(result) :
            self.factory.subscribe(info.id, info.key)
        def on_failed(reason) :
            log.err('Failed to save device {0}. Reason: {1}.'.format(info, reason))
        self.factory.device_save(info).addCallbacks(on_subscribe, on_failed)
    
    def on_command(self, deviceguid, command, finished):
        finished.errback(NotImplementedError())
    
    def notify1(self, name, **kwargs):
        dev = self.device_info()[0]
        # self.factory.notify(name, kwargs, device_id = dev.id)
    
    def notify2(self, name, **kwargs):
        dev = self.device_info()[1]
        # self.factory.notify(name, kwargs, device_id = dev.id)


i = 0
def looping_call(hnd):
    global i
    print ('Sending looping notification {0}.'.format(i))
    hnd.notify1('looping_notification_dev1', count = i, one_more_parameter = 'parameter_value')
    hnd.notify2('looping_notification_dev2', count = i, one_more_parameter = 'parameter_value')
    i += 1



def create_factory(use_ws, handler) :
    if use_ws :
        return devicehive.ws.WebSocketFactory(handler)
    else :
        return devicehive.poll.PollFactory(handler)

def main():
    log.startLogging(sys.stdout)
    handler = LogicHandler()
    factory = create_factory(True, handler)
    reactor.connectDeviceHive('http://ecloud.dataart.com/ecapi8/', factory)
    #
    lc = task.LoopingCall(looping_call, handler)
    # lc.start(10)
    #
    reactor.run()


if __name__ == '__main__' :
    main()

