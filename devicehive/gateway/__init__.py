# -*- encoding: utf8 -*-
# vim: set et tabstop=4 shiftwidth=4 nu nowrap: fileencoding=utf-8 encoding=utf-8

import devicehive
from zope.interface import Interface, Attribute


class GatewayError(Exception):
    def __init__(self, msg = 'unknown'):
        super(GatewayError, self).__init__('Got gateway error. Reason: {0}.'.format(msg))


class IDeviceInfo(Interface):
    device_id = Attribute('Device ID')
    device_key = Attribute('Device Key')
    device_name = Attribute('Device Name')
    device_status = Attribute('Device Status')
    network_name = Attribute('Network Name')
    network_description = Attribute('Network Description')
    network_key = Attribute('Network Key')
    device_class_name = Attribute('Device Class Name')
    device_class_version = Attribute('Device Class Version')
    device_class_is_permanent = Attribute('Whether Device Class is Permanent')
    offline_timeout = Attribute('Offline Timeout')
    equipment = Attribute('Device Equipment List') 


class INotification(Interface):
    name = Attribute('Notification Name')
    parameters = Attribute('Dictionary of Notification Parameters')


class BaseGateway(object):
    """
    Base implementation of gateway object.
    """
    
    class _DeviceDelegate(devicehive.DeviceDelegate):
        def __init__(self, gateway):
            super(BinaryFactory._DeviceDelegate, self).__init__()
            self.gateway = gateway
            self.info = None
        
        def device_id(self):
            return self.info.device_id if not self.info is None else None
        
        def device_key(self):
            return self.info.device_key if not self.info is None else None
        
        def device_name(self):
            return self.info.device_name if not self.info is None else None
        
        def device_status(self):
            return self.info.device_status if not self.info is None else None
        
        def network_name(self):
            return self.info.network_name if not self.info is None else None
        
        def network_description(self):
            return self.info.network_description if not self.info is None else None
        
        def network_key(self):
            return self.info.network_key if not self.info is None else None
        
        def device_class_name(self):
            return self.info.device_class_name if not self.info is None else None
        
        def device_class_version(self):
            return self.info.device_class_version if not self.info is None else None
        
        def device_class_is_permanent(self):
            return self.info.device_class_is_permanent if not self.info is None else None
        
        def offline_timeout(self):
            return self.info.offline_timeout if not self.info is None else None
        
        def equipment(self):
            return self.info.equipment if not self.info is None else None
        
        def do_command(self, command, finish_deferred):
            self.gateway.do_command(self, command, finish_deferred)
    
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
        """
        Method is called when new registration request comes from device(es).
        Method could be overridden in subclass to change device registration behaviour
        or device registration information.
        """
        device = BaseGateway._DeviceDelegate(self, device_info)
        factory = self.factory_cls(device = device)
        self.connect(device, factory)
    
    def connect(self, device, factory):
        """
        Connects device to DeviceHive server using ProtocolClientFactory passed into
        Gateway constructor.
        """
        id = device.info.device_id
        if not id in self.devices :
            self.devices[id] = BaseGateway._Item(device, factory)
            reactor.connectDeviceHive(self.url, factory)
        else :
            raise NotImplementedError('TODO: device tries to reconnect to device-hive.')
    
    def notification_received(self, device_info, notification):
        """
        Method is called by the device.
        """
        id = device_info.device_id
        if id in self.devices :
            self.devices[id].device.notify(notification.name, **notification.parameters)
    
    def do_command(self, sender, command, finish_deferred):
        """
        Method is called when devicehive calls command on device.
        """
        if not self.device_factory is None :
            id = sender.info.device_id
            if id in self.devices :
                self.device_factory.do_command(sender.info, command, finish_deferred)
            else :
                raise GatewayError('unknwon device {0}'.format(id))
        else :
            raise GatewayError('channel to device is not established')
    
    def run(self, transport_endpoint, device_factory):
        """
        Establishes connection to device(es)
        """
        self.device_factory = device_factory
        transport_endpoint.listen(device_factory)


__all__ ['IDeviceInfo', 'INotification', 'BaseGateway']


