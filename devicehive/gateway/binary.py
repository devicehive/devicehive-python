# -*- encoding: utf8 -*-
# vim: set et tabstop=4 shiftwidth=4 nu nowrap: fileencoding=utf-8 encoding=utf-8

import struct
import array
import uuid
import devicehive
from devicehive.gateway import IDeviceInfo
from zope.interface import Interface, implements, Attribute
from twisted.internet import interfaces, defer
import twisted.internet.serialport
from twisted.internet.protocol import ServerFactory, Protocol
from twisted.python.constants import Values, ValueConstant


class PacketError(Exception):
    def __init__(self, msg=None):
        super(PacketError, self).__init__(self, msg)


class IncompletePacketError(PacketError):    
    def __init__(self, msg=None):
        super(IncompletePacketError, self).__init__(msg)


class InvalidPacketLengthError(PacketError):
    def __init__(self, msg=None):
        super(InvalidPacketLengthError, self).__init__(msg)


class InvalidSignatureError(PacketError):
    def __init__(self, msg=None):
        super(InvalidSignatureError, self).__init__(msg)


class InvalidCRCError(PacketError):
    def __init__(self, msg=None):
        super(InvalidCRCError, self).__init__(msg)


class SystemIntents(Values):
    """
    System defined intents
    """
    RequestRegistration = ValueConstant(0)
    Register = ValueConstant(1)
    NotifyCommandResult = ValueConstant(2)


PACKET_SIGNATURE         = 0xc5c3
PACKET_SIGNATURE_HI      = 0xc5
PACKET_SIGNATURE_LO      = 0xc3

PACKET_OFFSET_SIGN_MSB   = 0
PACKET_OFFSET_SIGN_LSB   = 1
PACKET_OFFSET_VERSION    = 2
PACKET_OFFSET_FLAGS      = 3
PACKET_OFFSET_LEN_LSB    = 4
PACKET_OFFSET_LEN_MSB    = 5
PACKET_OFFSET_INTENT_LSB = 6
PACKET_OFFSET_INTENT_MSB = 7
PACKET_OFFSET_DATA       = 8

EMPTY_PACKET_LENGTH      = 9


class DataTypes(Values):
    """
    DeviceHive system data-types
    """
    Null = ValueConstant(0)
    Byte = ValueConstant(1)
    Word = ValueConstant(2)
    Dword = ValueConstant(3)
    Qword = ValueConstant(4)
    SignedByte = ValueConstant(5)
    SignedWord = ValueConstant(6)
    SignedDword = ValueConstant(7)
    SignedQword = ValueConstant(8)
    Single = ValueConstant(9)
    Double = ValueConstant(10)
    Boolean = ValueConstant(11)
    Guid = ValueConstant(12)
    String = ValueConstant(13)
    Binary = ValueConstant(14)
    Array = ValueConstant(15)


class AbstractPacket(object):
    signature = property(fget = lambda self : 0)
    
    version = property(fget = lambda self : 0)
    
    flags = property(fget = lambda self : 0)
    
    length = property(fget = lambda self : len(self.data))
    
    intent = property(fget = lambda self : 0)
    
    data = property(fget = lambda self : bytearray())
    
    def __len__(self):
        return self.length
    
    def checksum():
        def fget(self):
            s = ((self.signature & 0xff00) >> 8) + \
                self.signature + \
                self.version + \
                self.flags + \
                ((self.length & 0xff00) >> 8) + \
                self.length + \
                ((self.intent & 0xff00) >> 8) + \
                self.intent
            s += sum(self.data)
            return (0xff - (s & 0xff)) & 0xff
        return locals()
    checksum = property(**checksum())
    
    def to_binary(self):
        _len  = self.length
        _data = [x for x in self.data]
        _intent = self.intent
        return bytearray([((self.signature & 0xff00) >> 8) & 0xff,
                    self.signature & 0xff,
                    self.version & 0xff,
                    self.flags & 0xff,
                    _len & 0xff, ((_len & 0xff00) >> 8),
                    _intent & 0xff, ((_intent & 0xff00) >> 8)] + _data + [self.checksum,]) 


class Packet(AbstractPacket):
    def __init__(self, sign, ver, flags, intent, data):
        self._signature = sign
        self._version = ver
        self._flags = flags
        self._intent = intent
        self._data = data
    
    signature = property(fget = lambda self : self._signature)

    version = property(fget = lambda self : self._version)

    flags = property(fget = lambda self : self._flags)

    intent = property(fget = lambda self : self._intent)
    
    data = property(fget = lambda self : self._data)

    @staticmethod
    def from_binary(binstr):
        binstr_len = len(binstr)
        if binstr_len < EMPTY_PACKET_LENGTH :
            raise IncompletePacketError()
        signature = ((binstr[PACKET_OFFSET_SIGN_MSB] & 0xff) << 8) | (binstr[PACKET_OFFSET_SIGN_LSB] & 0xff)
        if signature != PACKET_SIGNATURE :
            raise InvalidSignatureError()
        version = binstr[PACKET_OFFSET_VERSION]
        flags   = binstr[PACKET_OFFSET_FLAGS]
        payload_len = ((binstr[PACKET_OFFSET_LEN_MSB] & 0xff) << 8) | (binstr[PACKET_OFFSET_LEN_LSB] & 0xff)
        if binstr_len < (EMPTY_PACKET_LENGTH + payload_len) :
            raise InvalidPacketLengthError()
        intent = ((binstr[PACKET_OFFSET_INTENT_MSB] & 0xff) << 8) | (binstr[PACKET_OFFSET_INTENT_LSB] & 0xff)
        frame_data = bytearray(binstr[PACKET_OFFSET_DATA:(PACKET_OFFSET_DATA + payload_len)])
        if 0xff != (sum(binstr[0: PACKET_OFFSET_DATA + payload_len + 1]) & 0xff) :
            raise InvalidCRCError()
        return Packet(signature, version, flags, intent, frame_data)


class RegistrationRequestPacket(AbstractPacket):
    """
    This packet is send from gateway to device in order to notify device
    that gateway works and ready.
    """
    
    def __init__(self):
        pass
    
    signature = property(fget = lambda self : PACKET_SIGNATURE)
    
    version = property(fget = lambda self : 1)
    
    flags = property(fget = lambda self : 0)
    
    intent = property(fget = lambda self : SystemIntents.RegistrationRequest)
    
    data = property(fget = lambda self : [])


class BinaryPacketBuffer(object):
    """
    Implements operations with packet buffer
    """
    
    def __init__(self):
        self._data = []
    
    data = property(fget = lambda self : self._data)
    
    def append(self, value):
        self._data.extend(value)
        self._skip_to_next_packet()
    
    def _skip_to_next_packet(self):
        data_len = len(self._data)
        if data_len > 1:
            # this line is not neccessary but i think this would be better than deleting void list (del _data[:0])
            if self._data[0] == PACKET_SIGNATURE_HI and self._data[1] == PACKET_SIGNATURE_LO :
                return
            idx = -1
            try:
                idx = self._data.index(PACKET_SIGNATURE_HI)
                if idx == data_len - 1 :
                    del self._data[:idx]
                elif idx < data_len - 2 :
                    if self._data[idx + 1] == PACKET_SIGNATURE_LO:
                        del self._data[:idx]
                    else :
                        del self._data[:idx + 1]
                        self._skip_to_next_packet()
            except ValueError:
                self._data = []
        elif data_len == 1 and self._data[0] != PACKET_SIGNATURE_HI:
            self._data = []
    
    def has_packet(self):
        """
        Determines whether the buffer contains a complete packet
        """
        data_len = len(self._data)
        if data_len < EMPTY_PACKET_LENGTH :
            return False
        payload_len = ((self._data[PACKET_OFFSET_LEN_MSB] << 8) & 0xff00) | (self._data[PACKET_OFFSET_LEN_LSB] & 0xff)
        if data_len < payload_len + EMPTY_PACKET_LENGTH:
            return False
        return True
    
    def clear(self):
        self._data = []
    
    def pop_packet(self):
        """
        Returns first received packet and then removes it from the buffer
        """
        if not self.has_packet() :
            return None
        msg = Packet.from_binary(self._data)
        del self._data[:PACKET_OFFSET_DATA + 1 + (((self._data[PACKET_OFFSET_LEN_MSB] << 8) & 0xff00) | (self._data[PACKET_OFFSET_LEN_LSB] & 0xff))]
        self._skip_to_next_packet()
        return msg


class AbstractBinaryProperty(property):
    def __init__(self, type, fget = None, fset = None):
        property.__init__(self, fget, fset)
        self.type = type


class binary_property(AbstractBinaryProperty):
    """
    Defines binary serializable property
    """
    def __init__(self, type, fget = None, fset = None):
        AbstractBinaryProperty.__init__(self, type, fget, fset)


class array_binary_property(AbstractBinaryProperty):
    """
    Defines binary serializable property of DataTypes.Array type
    """
    def __init__(self, element_type, fget = None, fset = None):
        AbstractBinaryProperty.__init__(self, DataTypes.Array, fget, fset)
        self.element_type = element_type


class BinaryFormatterError(Exception):
    def __init__(self, msg = None):
        super(BinarySerializerError, self).__init__(msg)


class BinarySerializationError(BinaryFormatterError):
    def __init__(self, reason = 'unexpected exception'):
        super(BinarySerializationError, self).__init__('Failed to serialize an object. Reason: {0}.'.format(reason))


class BinaryDeserializationError(BinaryFormatterError):
    def __init__(self, reason = 'unexpected exception'):
        super(BinaryDeserializationError, self).__init__('Failed to deserialize an object. Reason: {0}.'.format(reason))


class BinaryFormatter(object) :
    """
    Class provides method to serialize and deserialize binary payload into and from python objects
    """
    
    __basic_type_map__ = {DataTypes.Byte: ('B', 1),
                          DataTypes.Word: ('<H', 2),
                          DataTypes.Dword: ('<I', 4),
                          DataTypes.Qword: ('<Q', 8),
                          DataTypes.SignedByte: ('b', 1),
                          DataTypes.SignedWord: ('<h', 2),
                          DataTypes.SignedDword: ('<i', 4),
                          DataTypes.SignedQword: ('<q', 8),
                          DataTypes.Single: ('f', 4),
                          DataTypes.Double: ('d', 8),
                          DataTypes.Boolean: ('?', 1)}
    
    @staticmethod
    def serialize(obj) :
        """
        Serializes python object into binary form
        
        @param obj may be a python object or an array (list or tuple)
        """
        result = bytearray()
        if isinstance(obj, list) or isinstance(obj, tuple) :
            array_len = len(obj)
            result.extend(struct.pack('<H', array_len))
            for element in obj :
                result.extend(BinaryFormatter.serialize(element))
        elif hasattr(obj, '__binary_struct__') :
            for prop in obj.__binary_struct__ :
                if not isinstance(prop, AbstractBinaryProperty) :
                    raise BinarySerializationError('property {0} should be of AbstractBinaryProperty type'.format(prop))
                if prop.type == DataTypes.Null :
                    pass
                elif prop.type in BinaryFormatter.__basic_type_map__ :
                    packstr = BinaryFormatter.__basic_type_map__[prop.type][0]
                    result.extend(struct.pack(packstr, prop.__get__(obj)))
                elif prop.type == DataTypes.Guid :
                    guid = prop.__get__(obj)
                    if isinstance(guid, uuid.UUID) :
                        guid = guid.bytes
                    elif len(guid) != 16 :
                        raise BinarySerializationError('guid property should of uuid.UUID type or be an array of 16 elements')
                    result.extend(guid)
                elif prop.type == DataTypes.String :
                    str = prop.__get__(obj)
                    bstr = array.array('B', str)
                    bstr_len = len(bstr)
                    result.extend(struct.pack('<H', bstr_len))
                    result.extend(bstr)
                elif prop.type == DataTypes.Binary :
                    str = prop.__get__(obj)
                    str_len = len(str)
                    result.extend(struct.pack('<H', str_len))
                    result.extend(str)
                elif prop.type == DataTypes.Array :
                    result.extend(BinaryFormatter.serialize(prop.__get__(obj)))
                else :
                    BinarySerializationError('unsupported property type {0}'.format(prop.type))
        else :
            raise BinarySerializationError('unsupported type {0}.'.format(type(obj)))
        return result
    
    @staticmethod
    def deserialize(data, type):
        """
        Deserilizes @data array into object of type @type
        @param data - binary string/constant byte array/tuple or list
        @type  type - type in which binary string would be deserialized
        """
        def _deserialize(data, type, offset = 0):
            if hasattr(type, '__binary_struct__') :
                obj = type()
                for prop in obj.__binary_struct__ :
                    if prop.type == DataTypes.Null :
                        pass
                    elif prop.type in BinaryFormatter.__basic_type_map__ :
                        packstr, datalen = BinaryFormatter.__basic_type_map__[prop.type]
                        value = struct.unpack_from(packstr, data, offset)[0]
                        prop.__set__(obj, value)
                        offset += datalen
                    elif prop.type == DataTypes.Guid :
                        value = struct.unpack_from('B' * 16, data, offset)
                        fields = ((value[0] << 24) | (value[1] << 16) | (value[2] << 8) | (value[3]),
                         (value[4] << 8) | value[5], (value[6] << 8) | value[7], value[8], value[9], (value[10] << 40) | (value[11] << 32) | (value[12] << 24) | (value[13] << 16) | (value[14] << 8) | value[15])
                        prop.__set__(obj, uuid.UUID(fields = fields))
                        offset += 16
                    elif prop.type == DataTypes.String :
                        strlen = struct.unpack_from('<H', data, offset)[0]
                        offset += 2
                        bstr = bytearray(data[offset:offset + strlen])
                        offset += strlen
                        prop.__set__(obj, bstr.decode('utf-8'))
                    elif prop.type == DataTypes.Binary :
                        binlen = struct.unpack_from('<H', data, offset)[0]
                        offset += 2
                        bin = data[offset:offset + binlen]
                        offset += binlen
                        prop.__set__(obj, bin)
                    elif prop.type == DataTypes.Array :
                        if not isinstance(prop, array_binary_property) :
                            raise BinarySerializerError('Failed to deserialize array property {0}. Reason: property must be defined using array_binary_property function.'.format(prop))
                        arrlen = struct.unpack_from('<H', data, offset)[0]
                        offset += 2
                        value = []
                        for i in range(0, arrlen) :
                            subobj, offset = _deserialize(data, prop.element_type, offset)
                            value.append(subobj)
                        prop.__set__(obj, list(value))
                    else :
                        raise BinarySerializerError('Failed to deserialize property {0}. Reason: unsupported property type {1}.'.format(prop, prop.type))
                return (obj, offset)
            else :
                raise BinarySerializerError('Failed to deserialize an object. Reason: unsupported type {0}.'.format(type))
            return None
        data = array.array('B', data)
        obj, offset = _deserialize(data, type)
        return obj


def define_accessors(field):
    def fget(self):
        return getattr(self, field)
    def fset(self, value):
        setattr(self, field, value)
    return (fget, fset)


class Parameter(object):
    def __init__(self, type = DataTypes.Null, name = ''):
        self._type = type
        self._name = name
    
    type = binary_property(DataTypes.Byte, *define_accessors('_type'))
    
    name = binary_property(DataTypes.String, *define_accessors('_name'))
    
    __binary_struct__ = (type, name)


class Equipment(object):
    def __init__(self, name, code, typename):
        self._name = name
        self._code = code
        self._typename = typename
    
    name = binary_property(DataTypes.String, *define_accessors('_name'))
    
    code = binary_property(DataTypes.String, *define_accessors('_code'))
    
    typename = binary_property(DataTypes.String, *define_accessors('_typename'))
    
    __binary_struct__ = (name, code, typename)


class Notification(object):
    def __init__(self, intent, name, parameters):
        self._intent = intent
        self._name = name
        self._parameters = parameters
    
    intent = binary_property(DataTypes.Word, *define_accessors('_intent'))
    
    name = binary_property(DataTypes.String, *define_accessors('_name'))
    
    parameters = array_binary_property(Parameter, *define_accessors('_parameters'))
    
    __binary_struct__ = (intent, name, parameters)


class Command(object):
    def __init__(self, intent = 0, name = '', parameters = []):
        self._intent = intent
        self._name = name
        self._parameters = parameters
    
    intent = binary_property(DataTypes.Word, *define_accessors('_intent'))
    
    name = binary_property(DataTypes.String, *define_accessors('_name'))
    
    parameters = array_binary_property(Parameter, *define_accessors('_parameters'))
    
    __binary_struct__ = (intent, name, parameters)


class RegistrationPayload(object):
    """
    Payload of device registration response which is sent from device to gateway
    """
    
    def __init__(self):
        self._device_id = uuid.uuid1()
        self._device_key = ''
        self._device_name = ''
        self._device_class_name = ''
        self._device_class_version = ''
        self._equipment = list()
        self._notification = list()
        self._commands = list()
    
    device_id = binary_property(DataTypes.Guid, *define_accessors('_device_id'))
    
    device_key = binary_property(DataTypes.String, *define_accessors('_device_key'))
    
    device_name = binary_property(DataTypes.String, *define_accessors('_device_name'))
    
    device_class_name = binary_property(DataTypes.String, *define_accessors('_device_class_name'))
    
    device_class_version = binary_property(DataTypes.String, *define_accessors('_device_class_version'))
    
    equipment = array_binary_property(Equipment, *define_accessors('_equipment'))
    
    notifications = array_binary_property(Notification, *define_accessors('_notification'))
    
    commands = array_binary_property(Command, *define_accessors('_commands'))
    
    __binary_struct__ = (device_id, device_key, device_name, device_class_name, device_class_version, equipment, notifications, commands)


class NotificationCommandResultPayload(object):
    """
    Payload format of NotificationCommandResult message
    """
    def __init__(self):
        self._command_id = 0
        self._status     = ''
        self._result     = ''
    
    command_id = binary_property(DataTypes.Dword, *define_accessors('_command_id'))
    
    status = binary_property(DataTypes.String, *define_accessors('_status'))
    
    result = binary_property(DataTypes.String, *define_accessors('_result'))
    
    __binary_struct__ = (command_id, status, result)


class BinaryProtocol(Protocol):
    """
    Binary protocol implementation.
    """
    
    def __init__(self, factory):
        self.factory = factory
    
    def dataReceived(self, data):
        """
        Method should throws events to the factory when complete packet is received
        """
        self.factory.packet_buffer.append(data)
        while self.factory.packet_buffer.has_packet() :
            self.factory.packet_received(self.factory.packet_buffer.pop_packet())
    
    def connectionLost(self, reason):
        Protocol.connectionLost(self, reason)
    
    def makeConnection(self, transport):
        Protocol.makeConnection(self, transport)
    
    def send_command(self, intent, command_bin):
        """
        Sends binary data into transport channel
        """
        msg = Packet(PACKET_SIGNATURE, 1, 0, intent, bin)
        self.transport.write(msg.to_binary())
    
    def connectionMade(self):
        """
        Called when connection is made. Right after channel has been established gateway need to 
        send registration request intent to device(s).
        """
        pkt = RegistrationRequestPacket()
        self.transport.write(pkt.to_binary())


class AutoClassFactory(object):
    """
    Class is used to generate binary serializable classes
    """
    
    def _generate_binary_property(self, paramtype, fieldname):
        def getter(self):
            return getattr(self, fieldname)
        def setter(self, value):
            setattr(self, fieldname, value)
        return binary_property(paramtype, fget = getter, fset = setter)
    
    def generate(self, command):
        members = dict({'__binary_struct__': list()})
        for param in command.parameters :
            fieldname = '_{0}'.format(param.name)
            paramtype = param.type
            if paramtype == DataTypes.Array :
                raise NotImplementedError('Array properties in automatic classes are not supported.')
            else :
                members[fieldname]  = None
                members[param.name] = prop = self._generate_binary_property(param.type, fieldname)
                members['__binary_struct__'].append(prop)
        return type('{0}Class'.format(command.name), (object,), members)
    
    def generate_reginfo(self, reg):
        pass


def autoclass_update_properties(obj, cmd):
    """
    Applies dictionary values to corresponding object properties.
    """
    props = [(prop[0], cmd[prop[1]]) for prop in [(getattr(obj.__class__, pname), pname) for pname in dir(obj.__class__)]
                                            if isinstance(prop[0], AbstractBinaryProperty) and
                                            prop[0] in obj.__binary_struct__ and
                                            cmd.has_key(prop[1])]
    for prop in props :
        prop[0].__set__(obj, prop[1])
    return obj


class BinaryFactory(ServerFactory):
    class _DeviceInfo(object):
        def __init__(self, device_id = '', device_key = '', device_name = '', device_status = '', \
                     network_name = None, network_descr = None, network_key = None, devcls_name = '', \
                     devcls_version = '', devcls_is_permanent = False, offline_timeout = None, equipment = []):
            self.device_id = device_id
            self.device_key = device_key
            self.device_name = device_name
            self.device_status = device_status
            self.network_name = network_name
            self.network_description = network_descr
            self.network_key = network_key
            self.device_class_name = devcls_name
            self.device_class_version = devcls_version
            self.device_class_is_permanent = devcls_is_permanent
            self.offline_timeout = offline_timeout
            self.equipment = equipment    
    
    class _CommandItem(object):
        def __init__(self, intent = 0, cls = None):
            self.intent = intent
            self.cls = None
    
    def __init__(self, gateway):
        self.packet_buffer = BinaryPacketBuffer()
        self.protocol = None
        self.gateway = gateway
        self.command_descriptors = {}
    
    def register_command_descriptor(self, command_name, binary_class):
        """
        Method is specific for binary protocol. It allows specify custom deserialization
        description for the command's payload.
        """
        self.command_descriptors[command_name] = BinaryFactory._CommandItem(intent = -1, cls = binary_class)
    
    def handle_registration_received(self, reg):
        """
        Adds command to binary-serializable-class mapping and then
        calls deferred object.
        """
        autoclass_factory = AutoClassFactory()
        for command in reg.commands:
            if not command.name in self.command_descriptors :
                cls = autoclass_factory.generate(command)
                self.command_descriptors[command.name] = BinaryFactory._CommandItem(command.intent, cls)
            else :
                self.command_descriptors[command.name].intent = command.intent
        info = BinaryFactory._DeviceInfo(self, device_id = str(reg.device_id), \
                                device_key = reg.device_key, \
                                device_name = reg.device_name, \
                                device_status = 'Online', \
                                devcls_name = reg.device_class_name, \
                                devcls_version = reg.device_class_version, \
                                equipment = [devicehive.Equipment(e.name, e.code, e.typename) for e in reg.equipment])
        self.gateway.registration_hook(info)
        device_delegate = BinaryFactory._DeviceDelegate(self, info)
        self.gateway.registration_received(device_delegate)
    
    def handle_notification_command_result(self, notifreq):
        """
        Run all callbacks attached to notification_reveived deferred
        """
        self._notification_received.callback(None)
    
    def packet_received(self, packet):
        if packet.intent == SystemIntents.Register :
            regreq = BinaryFormatter.deserialize(packet.data, RegistrationPayload)
            self.handle_registration_received(regreq)
        elif packet.intent == SystemIntents.NotifyCommandResult :
            notifreq = BinaryFormatter.deserialize(packet.data, NotificationCommandResultPayload)
            self.handle_notification_command_result(notifreq)
        else:
            pass
    
    def do_command(self, command, finish_deferred):
        """
        This handler is called when a new command comes from DeviceHive server
        """
        command_name = command['command']
        parameters = command['parameters']
        if command_name in self.command_descriptors :
            command_desc = self.command_descriptors[command_name]
            command_obj = command_desc.cls()
            autoclass_update_properties(command_obj, parameters)
            self.protocol.send_command(command_desc.intent, command_bin)
        else :
            finish_deferred.errback()
    
    def buildProtocol(self, addr):
        self.protocol = BinaryProtocol(self) 
        return self.protocol
    
    registration_received = property(fget = lambda self : self._registration_received)
    
    notification_received = property(fget = lambda self : self._notification_received)


class SerialPortAddress(object):
    """
    Stores serial port address and options
    """
    
    implements(interfaces.IAddress)
    
    def __init__(self, port, **port_opts):
        """
        @param port: The port address
        @param port_opts: Dictionary of serial port options as they passed
                        into serial.SerialPort constructor
        """
        self.port = port
        self.port_options = port_opts


class SerialPortEndpoint(object):
    """
    Serial port Input/Output endpoint

    Usage example:
        endpoint = SerialPortEndpoint(reactor, 'COM10', baud_rate=9600)
        endpoint.listen( BinaryProtocolFactory )
        reactor.run()
    """
    implements(interfaces.IStreamServerEndpoint)

    def __init__(self, reactor, port, **port_opts):
        """
        @param reactor: The reactor for the endpoint
        @param port: Port name
        @param port_args: Dictionary of port parameters
        """
        self._reactor = reactor
        self._port_addr = SerialPortAddress(port, **port_opts)
    
    def listen(self, protoFactory):
        proto = protoFactory.buildProtocol(self._port_addr)
        return defer.execute(serial.SerialPort, proto, self._port_addr.port, self._reactor, **self._port_addr.port_options)


