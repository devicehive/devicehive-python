# -*- encoding: utf8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8 encoding=utf-8


from zope.interface import Interface, Attribute


class ICommand(Interface):
    id = Attribute('Command identifier')
    timestamp = Attribute('Command timestamp (UTC)')
    user_id = Attribute('Associated user identifier')
    command = Attribute('Command name')
    parameters = Attribute('Command parameters, a dict object with an arbitrary structure')
    lifetime = Attribute('Command lifetime, a number of seconds until this command expires')
    flags = Attribute('Command flags, and optional value that could be supplied for device or related infrastructure')
    status = Attribute('Command status, as reported by device or related infrastructure')
    result = Attribute('Command execution result, and optional value that could be provided by device')
    
    def to_dict(self):
        """
        @return dict representation of the object
        """


class ICommandResult(Interface):
    status = Attribute('Status')
    result = Attribute('Command result. May be a string or an object.')
    def to_dict(self):
        """
        @return dict representation of the object
        """


class INetwork(Interface):
    id = Attribute('Network identifier')
    key = Attribute('Optional key that is used to protect the network from unauthorized device registrations')
    name = Attribute('Network display name')
    description = Attribute('Network description')
    
    def to_dict(self):
        """
        @return dict representation of the object
        """


class IEquipment(Interface):
    name = Attribute('Equipment display name')
    code = Attribute('Equipment code')
    type = Attribute('Equipment type')
    data = Attribute('Equipment data, a dict object with an arbitrary structure')
    
    def to_dict(self):
        """
        @return dict representation of the object
        """


class IDeviceClass(Interface):
    def to_dict(self):
        """
        @return dict representation of the object
        """        


class IDeviceInfo(Interface):
    id = Attribute('Device ID')
    key = Attribute('Device Key')
    name = Attribute('Device Name')
    status = Attribute('Device Status')
    data = Attribute('Device data, a dict object with an arbitrary structure')
    network = Attribute('Network identifier or Network object')
    device_class = Attribute('device class identifier or device cass object')
    equipment = Attribute('List of IEquipment objects')
    
    def to_dict(self):
        """
        @return dict representation of the object
        """


class IProtoHandler(Interface):
    factory = Attribute('Reference to the owned factory/object which implements IProtoFactory')
    
    def on_failure(self, reason):
        """
        Called as a reaction on any unhandled error
        """
    
    def on_apimeta(self, websocket_server, server_time):
        """
        Reaction on ApiMeta call.
        
        @param websocket_server - url of devicehive websocket server
        @param server_time - current server time
        """
    
    def on_connected(self):
        """
        This callback is called upon connection has been established.
        """
    
    def on_closing_connection(self):
        """
        Called when server wants to close transport connection.
        """
    
    def on_command(self, deviceguid, command, finished):
        """
        Is called in reaction to command/insert received from devicehive server.
        
        @param deviceguid - Device unique identifier.
        @param command - ICommand object.
        @param finished - deferred object. When command finishes its execution user has to call this deferred's callback.
        """


class IProtoFactory(Interface):
    def authenticate(self, device_id, device_key):
        """
        Sends authentication message.
        
        @param device_id - device id
        @param device_key - device key
        @return deferred
        """
    
    def notify(self, notification, params, device_id = None, device_key = None):
        """
        Sends notification message to devicehive server.
        
        @param notification - notification identifier
        @param param - dictionary of notification parameters
        @return deferred
        """
    
    def update_command(self, command, device_id = None, device_key = None):
        """
        Updates an existing device command.
        
        @return deferred
        """
    
    def subscribe(self, device_id = None, device_key = None):
        """
        Subscribes a device to commands.
        
        @return deferred
        """ 
    
    def unsubscribe(self, device_id = None, device_key = None):
        """
        Unsubscribe a device from commands reception.
        
        @return deferred
        """
    
    def device_save(self, deviec_info):
        """
        Registers or updates a device. A valid device key is required in the deviceKey parameter
        in order to update an existing device.
        
        @param device_info - object which implements IDeviceInfo interface
        @return deferred
        """

