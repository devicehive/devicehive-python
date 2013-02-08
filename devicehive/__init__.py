# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8 encoding=utf-8:

from zope.interface import implements
from twisted.internet import reactor
from devicehive.interfaces import INetwork, IDeviceClass, IDeviceInfo, INotification, IEquipment, IProtoHandler
from devicehive.utils import parse_url, url_path, EmptyDataProducer
from twisted.web.http_headers import Headers
from twisted.web.client import Request


__all__ = ['DhError',
           'connectDeviceHive', 
           'CommandResult',
           'Network',
           'DeviceClass',
           'Equipment',
           'DeviceInfo',
           'Notification']


class DhError(Exception):
    """
    It is supposed to be base exception type for entire devicehive library.
    """
    
    def __init__(self, msg = None) :
        super(DhError, self).__init__(msg)


def connectDeviceHive(device_hive_url, factory):
    """
    reactor.connectDeviceHive(device_hive_url, factory)
    """
    url, host, port = parse_url(device_hive_url)
    factory.uri = url
    factory.host = host
    factory.port = port
    return reactor.connectTCP(host, port, factory)
reactor.connectDeviceHive = connectDeviceHive


class CommandResult(object):
    def __init__(self, status, result = None):
        self._status = status
        self._result = result
    
    def to_dict(self):
        if self._result is not None :
            return {'status': str(self._status), 'result': str(self._result)}
        else :
            return {'status': str(self._status)}
    
    status = property(fget = lambda self : self._status)
    result = property(fget = lambda self : self._result)


class Network(object):
    
    implements(INetwork)
    
    def __init__(self, id = None, key = None, name = None, descr = None):
        self.id = id
        self.key = key
        self.name = None
        self.description = descr
    
    def to_dict(self):
        res = {'key': self.key, 'name': self.name, 'description': self.description}
        if self.id is not None :
            res['id'] = self.id
        return res


class DeviceClass(object):
    
    implements(IDeviceClass)
    
    def __init__(self, name = None, version = None, is_permanent = None):
        self.name = name
        self.version = version
        self.is_permanent = is_permanent
    
    def to_dict(self):
        res = {'name': self.name, 'version': self.version}
        if self.is_permanent is not None :
            res['is_permanent'] = self.is_permanent
        return res


class Equipment(object):
    
    implements(IEquipment)
    
    def __init__(self, name = None, code = None, type = None, data = None):
        self.name = name
        self.code = code
        self.type = type
        self.data = data
    
    def to_dict(self):
        res = {'name': self.name, 'code': self.code, 'type': self.type}
        if self.data is not None :
            res['data'] = self.data
        return res


class DeviceInfo(object):
    
    implements(IDeviceInfo)
    
    def __init__(self, id = None, key = None, name = None, status = None, data = None, network = None, device_class = None, equipment = None):
        self.id = id
        self.key = key
        self.name = name
        self.status = status
        self.data = data
        self.network = network
        self.device_class = device_class
        self.equipment = equipment
    
    def __str__(self):
            return '<id: "{0}", key: "{1}", name: "{2}", ... >'.format(self.id, self.key, self.name)
    
    def to_dict(self):
        res = {'key': self.key,
               'name': self.name}
        if self.status is not None :
            res['status'] = self.status
        if self.data is not None :
            res['data'] = data
        if self.network is not None :
            res['network'] = self.network.to_dict() if INetwork.implementedBy(self.network.__class__) else self.network
        res['deviceClass'] = self.device_class.to_dict() if IDeviceClass.implementedBy(self.device_class.__class__) else self.device_class
        if self.equipment is not None :
            res['equipment'] = [x.to_dict() for x in self.equipment]
        return res


class Notification(object):
    
    implements(INotification)
    
    def __init__(self, name = None, parameters = None):
        self.name = name
        self.parameters = parameters
    
    def __str__(self):
        return '<name: "{0}", parameters: {1}>'.format(self.name, self.parameters)
    
    def to_dict(self):
        return {'name': self.name, 'parameters': self.parameters}


class ApiInfoRequest(Request):
    def __init__(self, url, host):
        super(ApiInfoRequest, self).__init__('GET', url_path(url, 'info'), ApiInfoRequest.headers(host), EmptyDataProducer())
    
    @staticmethod
    def headers(host):
        return Headers({'Host': [host], 'Content-Type': ['application/json'], 'Accept': ['application/json']})

