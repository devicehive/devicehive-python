# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8 encoding=utf-8:

from twisted.internet import reactor
from twisted.python import log
import devicehive
from devicehive.interfaces import IProtoHandler
from zope.interface import Interface, Attribute, implements


__all__ = ['GatewayError', 'IGateway', 'BaseGateway']


class GatewayError(Exception):
    def __init__(self, msg = 'unknown'):
        super(GatewayError, self).__init__('Got gateway error. Reason: {0}.'.format(msg))


class IGateway(Interface):
    def registration_received(self, info):
        """
        Method is called when new registration request comes from device(es).
        Method could be overridden in subclass to change device registration behaviour
        or device registration information.
        
        @type info: C{object}
        @param info: A device registration information. It should implemet C{IDeviceInfo} interface.
        """
    
    def notification_received(self, device_info, notification):
        """
        Method is called when a device sends notification. Gateway can handle it at this point.
        
        @type device_info: C{object}
        @param device_info: A device information which implements C{IDeviceInfo} interface.
        
        @type notification: C{object}
        @param notification: A notification which was sent. It implements C{INotification} interface.
        """
    
    def do_command(self, sender, command, finish_deferred):
        """
        Method is called when devicehive sends a command to a device.
        
        @type sender: C{object}
        @param sender: C{IProtoHandler} object which reseived a command from a protocol-factory. 
        
        @type command: C{object}
        @param command: 
        
        @type finish_deferred: C{Deferred}
        @param finish_deferred:
        """


class BaseGateway(object):
    """
    Base implementation of gateway object.
    """
    
    implements(IGateway)
    
    class _ProtoHandler(object):
        """
        This class holds implementation of application logic.
        """
        
        implements(IProtoHandler)
        
        def __init__(self, gateway):
            self.gateway = gateway
            self.factory = None
        
        def on_failure(self, reason):
            pass
        
        def on_apimeta(self, websocket_server, server_time):
            pass
        
        def on_connected(self):
            pass
        
        def on_closing_connection(self):
            pass
        
        def on_command(self, deviceguid, command, finished):
            pass
    
    class _Item(object):
        def __init__(self, device = None, factory = None):
            self.device = device
            self.factory = factory
    
    def __init__(self, url, factory_cls) :
        super(BaseGateway, self).__init__()
        self.device_factory = None
        self.devices = {}
        self.url = url
        self.factory_cls = factory_cls
    
    def registration_received(self, device_info):
        log.msg('Device {0} has sent registration information.'.format(device_info))
        device = BaseGateway._DeviceDelegate(self, device_info)
        factory = self.factory_cls(handler = device)
        self.connect(device, factory)    
    
    def notification_received(self, device_info, notification):
        """
        Method is called by the device.
        """
        log.msg('Device {0} has sent notification {1}.'.format(device_info, notification))
        id = device_info.id
        if id in self.devices :
            self.devices[id].device.notify(notification.name, **notification.parameters)
    
    def do_command(self, sender, command, finish_deferred):
        """
        Method is called when devicehive calls command on device.
        """
        if not self.device_factory is None :
            id = sender.info.id
            if id in self.devices :
                self.device_factory.do_command(sender.info, command, finish_deferred)
            else :
                raise GatewayError('unknwon device {0}'.format(id))
        else :
            raise GatewayError('channel to device is not established')
    
    def connect(self, device, factory):
        """
        Connects device to DeviceHive server using ProtocolClientFactory passed into
        Gateway constructor.
        """
        id = device.info.id
        if not id in self.devices :
            self.devices[id] = BaseGateway._Item(device, factory)
            reactor.connectDeviceHive(self.url, factory)
        else :
            raise NotImplementedError('TODO: device tries to reconnect to device-hive.')
    
    def run(self, transport_endpoint, device_factory):
        """
        Establishes connection to device(es)
        """
        self.device_factory = device_factory
        transport_endpoint.listen(device_factory)

