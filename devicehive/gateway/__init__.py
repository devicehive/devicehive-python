# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

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
    
    def do_command(self, info, command, finish_deferred):
        """
        Method is called when devicehive sends a command to a device.
        
        @type info: C{object}
        @param info: C{IDeviceInfo} object which reseived a command from a protocol-factory. 
        
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
    
    device_factory = None
    factory = None
    connected = False
    devices = {}
    
    class _ProtoHandler(object):
        implements(IProtoHandler)
        
        factory = None
        gateway = None
        
        def __init__(self, gateway):
            self.gateway = gateway
        
        def on_apimeta(self, websocket_server, server_time):
            pass
        
        def on_connected(self):
            self.gateway.on_connected()
        
        def on_connection_failed(self, reason):
            pass
        
        def on_closing_connection(self):
            pass
        
        def on_command(self, device_id, command, finished):
            self.gateway.do_command(device_id, command, finished)
        
        def on_failure(self, device_id, reason):
            pass
    
    def __init__(self, url, factory_cls) :
        super(BaseGateway, self).__init__()
        self.factory = factory_cls(handler = BaseGateway._ProtoHandler(self))
        self.factory.connect(url)
    
    def connect_device(self, info):
        def on_subscribe(result) :
            self.factory.subscribe(info.id, info.key)
        def on_failed(reason) :
            log.err('Failed to save device {0}. Reason: {1}.'.format(info, reason))
        self.factory.device_save(info).addCallbacks(on_subscribe, on_failed)
    
    def on_connected(self):
        self.connected = True
        for key in self.devices :
            self.connect_device(self.devices[key])
    
    def registration_received(self, info):
        log.msg('Device {0} has sent registration information.'.format(info))
        self.devices[info.id] = info
        if self.connected :
            self.connect_device(info)
    
    def notification_received(self, info, notification):
        log.msg('Device {0} has sent notification {1}.'.format(info, notification))
        if self.connected :
            self.factory.notify(notification.name, notification.parameters, info.id, info.key)
    
    def do_command(self, device_id, command, finish_deferred):
        if device_id in self.devices :
            info = self.devices[device_id]
            self.device_factory.do_command(info, command, finish_deferred)
    
    def run(self, transport_endpoint, device_factory):
        self.device_factory = device_factory
        transport_endpoint.listen(device_factory)

