# -*- encoding: utf8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8 encoding=utf-8

import struct
import array
import uuid
import devicehive
import json
from collections import Iterable
from devicehive.gateway import IDeviceInfo, INotification
from zope.interface import Interface, implements, Attribute
from twisted.internet import interfaces, defer
import twisted.internet.serialport
from twisted.python import log
from twisted.internet.protocol import ServerFactory, Protocol
from twisted.python.constants import Values, ValueConstant
from twisted.internet.serialport import SerialPort


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


SYS_INTENT_REQUEST_REGISTRATION = 0
SYS_INTENT_REGISTER = 1
SYS_INTENT_NOTIFY_COMMAND_RESULT = 2
SYS_INTENT_REGISTER2 = 3


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


DATA_TYPE_NULL   = 0
DATA_TYPE_BYTE   = 1
DATA_TYPE_WORD   = 2
DATA_TYPE_DWORD  = 3
DATA_TYPE_QWORD  = 4
DATA_TYPE_SBYTE  = 5
DATA_TYPE_SWORD  = 6
DATA_TYPE_SDWORD = 7
DATA_TYPE_SQWORD = 8
DATA_TYPE_SINGLE = 9
DATA_TYPE_DOUBLE = 10
DATA_TYPE_BOOL   = 11
DATA_TYPE_GUID   = 12
DATA_TYPE_STRING = 13
DATA_TYPE_BINARY = 14
DATA_TYPE_ARRAY  = 15

DATA_TYPE_OBJECT = 16


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
    
    def __str__(self):
        return '<<intent:{0}, data_len:{1}>>'.format(self._intent, len(self._data))
    
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
    
    intent = property(fget = lambda self : SYS_INTENT_REQUEST_REGISTRATION)
    
    data = property(fget = lambda self : [])


class BinaryPacketBuffer(object):
    """
    Implements operations with packet buffer
    """
    
    def __init__(self):
        self._data = []
    
    data = property(fget = lambda self : self._data)
    
    def append(self, value):
        if isinstance(value, str) :
            value = [ord(x) for x in value]
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
        pkt = Packet.from_binary(self._data)
        del self._data[:PACKET_OFFSET_DATA + 1 + (((self._data[PACKET_OFFSET_LEN_MSB] << 8) & 0xff00) | (self._data[PACKET_OFFSET_LEN_LSB] & 0xff))]
        self._skip_to_next_packet()
        return pkt


class AbstractBinaryProperty(property):
    __DEFAULT_VALUE__ = {DATA_TYPE_NULL: None,
                         DATA_TYPE_BYTE: 0,
                         DATA_TYPE_WORD: 0,
                         DATA_TYPE_DWORD: 0,
                         DATA_TYPE_QWORD: 0,
                         DATA_TYPE_SBYTE: 0,
                         DATA_TYPE_SWORD: 0,
                         DATA_TYPE_SDWORD: 0,
                         DATA_TYPE_SQWORD: 0,
                         DATA_TYPE_SINGLE: 0.0,
                         DATA_TYPE_DOUBLE: 0.0,
                         DATA_TYPE_BOOL: False,
                         DATA_TYPE_GUID: uuid.uuid1(),
                         DATA_TYPE_STRING: '',
                         DATA_TYPE_BINARY: bytearray(),
                         DATA_TYPE_ARRAY: []}
    
    def __prop_counter():
        i = 0
        while True :
            yield '_property{0}'.format(i)
            i += 1
    __prop_counter = __prop_counter()
    
    def __init__(self, type, fget = None, fset = None):
        if (fget is None) and (fset is None) :
            fieldname = AbstractBinaryProperty.__prop_counter.next()
            fieldtype = type
            def getter(self):
                return getattr(self, fieldname, AbstractBinaryProperty.__DEFAULT_VALUE__[fieldtype])
            def setter(self, value):
                setattr(self, fieldname, value)
            fget = getter
            fset = setter
        super(AbstractBinaryProperty, self).__init__(fget, fset)
        self.type = type


class binary_property(AbstractBinaryProperty):
    """
    Defines binary serializable property. If a user provides BinarySerializable type into @type parameter
    then it would be serialized as a complex object or a structure.
    """
    def __init__(self, type, fget = None, fset = None):
        super(binary_property, self).__init__(type, fget, fset)


class array_binary_property(AbstractBinaryProperty):
    """
    Defines binary serializable property of Array type
    """
    def __init__(self, qualifier, fget = None, fset = None):
        super(array_binary_property, self).__init__(DATA_TYPE_ARRAY, fget, fset)
        self.qualifier = qualifier


class object_binary_property(AbstractBinaryProperty):
    """
    Defines complex object property
    """
    def __init__(self, qualifier, fget = None, fset = None):
        super(object_binary_property, self).__init__(DATA_TYPE_OBJECT, fget, fset)
        self.qualifier = qualifier


class BinaryFormatterError(Exception):
    def __init__(self, msg = None):
        super(BinaryFormatterError, self).__init__(msg)


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
    
    __basic_type_map__ = {DATA_TYPE_BYTE: ('B', 1),
                          DATA_TYPE_WORD: ('<H', 2),
                          DATA_TYPE_DWORD: ('<I', 4),
                          DATA_TYPE_QWORD: ('<Q', 8),
                          DATA_TYPE_SBYTE: ('b', 1),
                          DATA_TYPE_SWORD: ('<h', 2),
                          DATA_TYPE_SDWORD: ('<i', 4),
                          DATA_TYPE_SQWORD: ('<q', 8),
                          DATA_TYPE_SINGLE: ('f', 4),
                          DATA_TYPE_DOUBLE: ('d', 8),
                          DATA_TYPE_BOOL: ('?', 1)}
    
    __json_type_map__ = {'bool': DATA_TYPE_BOOL,
                         'u8': DATA_TYPE_BYTE, 'uint8': DATA_TYPE_BYTE,
                         'i8': DATA_TYPE_SBYTE, 'int8': DATA_TYPE_SBYTE,
                         'u16': DATA_TYPE_WORD, 'uint16': DATA_TYPE_WORD,
                         'i16': DATA_TYPE_SWORD, 'int16': DATA_TYPE_SWORD,
                         'u32': DATA_TYPE_DWORD, 'uint32': DATA_TYPE_DWORD,
                         'i32': DATA_TYPE_SDWORD, 'int32': DATA_TYPE_SDWORD,
                         'u64': DATA_TYPE_QWORD, 'uint64': DATA_TYPE_QWORD,
                         'i64': DATA_TYPE_SQWORD, 'int64': DATA_TYPE_SQWORD,
                         'f': DATA_TYPE_SINGLE, 'single': DATA_TYPE_SINGLE,
                         'ff': DATA_TYPE_DOUBLE, 'double': DATA_TYPE_DOUBLE,
                         'uuid': DATA_TYPE_GUID, 'guid': DATA_TYPE_GUID,
                         's': DATA_TYPE_STRING, 'str': DATA_TYPE_STRING, 'string': DATA_TYPE_STRING,
                         'b': DATA_TYPE_BINARY, 'bin': DATA_TYPE_BINARY, 'binary': DATA_TYPE_BINARY}
    
    def __class_counter():
        i = 0
        while True :
            yield 'AutoClass{0}'.format(i)
            i += 1
    __class_counter = __class_counter()
    
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
                if prop.type == DATA_TYPE_NULL :
                    pass
                elif prop.type in BinaryFormatter.__basic_type_map__ :
                    packstr = BinaryFormatter.__basic_type_map__[prop.type][0]
                    propval = prop.__get__(obj)
                    result.extend(struct.pack(packstr, propval))
                elif prop.type == DATA_TYPE_GUID :
                    guid = prop.__get__(obj)
                    if isinstance(guid, uuid.UUID) :
                        guid = guid.bytes
                    elif len(guid) != 16 :
                        raise BinarySerializationError('guid property should of uuid.UUID type or be an array of 16 elements')
                    result.extend(guid)
                elif prop.type == DATA_TYPE_STRING :
                    str = prop.__get__(obj)
                    bstr = array.array('B', str)
                    bstr_len = len(bstr)
                    result.extend(struct.pack('<H', bstr_len))
                    result.extend(bstr)
                elif prop.type == DATA_TYPE_BINARY :
                    str = prop.__get__(obj)
                    str_len = len(str)
                    result.extend(struct.pack('<H', str_len))
                    result.extend(str)
                elif prop.type == DATA_TYPE_ARRAY :
                    result.extend(BinaryFormatter.serialize(prop.__get__(obj)))
                else :
                    BinarySerializationError('unsupported property type {0}({1})'.format( type(prop.type), prop.type))
        else :
            raise BinarySerializationError('unsupported type {0}.'.format(type(obj)))
        return result
    
    @staticmethod
    def deserialize(data, cls):
        """
        Deserilizes @data array into object of type @type
        @param data - binary string/constant byte array/tuple or list
        @type  type - type in which binary string would be deserialized
        """
        def _deserialize(data, cls, offset = 0):
            if hasattr(cls, '__binary_struct__') :
                obj = cls()
                for prop in obj.__binary_struct__ :
                    if prop.type == DATA_TYPE_NULL :
                        pass
                    elif prop.type in BinaryFormatter.__basic_type_map__ :
                        packstr, datalen = BinaryFormatter.__basic_type_map__[prop.type]
                        value = struct.unpack_from(packstr, data, offset)[0]
                        prop.__set__(obj, value)
                        offset += datalen
                    elif prop.type == DATA_TYPE_GUID :
                        value = struct.unpack_from('B' * 16, data, offset)
                        fields = ((value[0] << 24) | (value[1] << 16) | (value[2] << 8) | (value[3]),
                         (value[4] << 8) | value[5], (value[6] << 8) | value[7], value[8], value[9], (value[10] << 40) | (value[11] << 32) | (value[12] << 24) | (value[13] << 16) | (value[14] << 8) | value[15])
                        prop.__set__(obj, uuid.UUID(fields = fields))
                        offset += 16
                    elif prop.type == DATA_TYPE_STRING :
                        strlen = struct.unpack_from('<H', data, offset)[0]
                        offset += 2
                        bstr = bytearray(data[offset:offset + strlen])
                        offset += strlen
                        prop.__set__(obj, bstr.decode('utf-8'))
                    elif prop.type == DATA_TYPE_BINARY :
                        binlen = struct.unpack_from('<H', data, offset)[0]
                        offset += 2
                        bin = data[offset:offset + binlen]
                        offset += binlen
                        prop.__set__(obj, bin)
                    elif prop.type == DATA_TYPE_ARRAY :
                        if not isinstance(prop, array_binary_property) :
                            raise BinaryDeserializationError('Failed to deserialize array property {0}. Reason: property must be defined using array_binary_property function.'.format(prop))
                        arrlen = struct.unpack_from('<H', data, offset)[0]
                        offset += 2
                        value = []
                        for i in range(0, arrlen) :
                            subobj, offset = _deserialize(data, prop.qualifier, offset)
                            value.append(subobj)
                        prop.__set__(obj, list(value))
                    else :
                        raise BinaryDeserializationError('Failed to deserialize property {0} in object {1}. Reason: unsupported property type {2} ({3}).'.format(prop, obj, type(prop.type), prop.type))
                return (obj, offset)
            else :
                raise BinaryDeserializationError('Failed to deserialize an object. Reason: unsupported type {0}.'.format(cls))
            return None
        data = array.array('B', data)
        obj, offset = _deserialize(data, cls)
        return obj
    
    @staticmethod
    def deserialize_json_basic_definition(json) :
        return BinaryFormatter.__json_type_map__[json]
    
    @staticmethod
    def deserialize_json_object_definition(json) :
        """
        Converts json object @value into BinarySerializable
        """
        if not isinstance(json, dict) :
            raise TypeError('dict expected')
        
        members = {'__binary_struct__': []}
        for prop_name in json :
            prop = BinaryFormatter.deserialize_json_definition(json[prop_name])
            members[prop_name] = prop
            members['__binary_struct__'].append(prop)
        
        return type(BinaryFormatter.__class_counter.next(), (object,), members)
    
    @staticmethod
    def deserialize_json_array_definition(json):
        if not (isinstance(json, list) or isinstance(json, tuple)) or len(json) != 1 :
            raise TypeError('List or tuple type expected. Got {0}.'.format(type(json)))
        etype = json[0]
        if isinstance(etype, dict) :
            return BinaryFormatter.deserialize_json_object_definition(etype)
        elif (isinstance(etype, tuple) or isinstance(etype, list)) and len(etype) == 1 :
            return array_binary_property(BinaryFormatter.deserialize_json_array_definition(etype))
        elif etype in BinaryFormatter.__json_type_map__ :
            return BinaryFormatter.__json_type_map__[etype]
        else :
            raise BinaryDeserializationError('Unsupported json array element {0}.'.format(etype))
    
    @staticmethod
    def deserialize_json_definition(json) :
        """
        Method returns binary_property, object_binary_property or array_binary_property
        """
        if isinstance(json, dict) :
            return object_binary_property( BinaryFormatter.deserialize_json_object_definition(json) )
        elif isinstance(json, list) or isinstance(json, tuple) :
            return array_binary_property( BinaryFormatter.deserialize_json_array_definition(json) )
        elif json in BinaryFormatter.__json_type_map__ :
            return binary_property( BinaryFormatter.deserialize_json_basic_definition(json) )
        else :
            raise BinaryDeserializationError('Unsupported json definition {0}.'.format(json))
    
    @staticmethod
    def deserialize_json_parameters(params) :
        """
        Method converts list of json parameter definitions into BinarySerializable structure
        """
        res = []
        for param_name in params :
            param_type = params[param_name]
            #
            param = Parameter()
            param.name = param_name
            # Determine parameter type
            if isinstance(param_type, dict) :
                param.type = DATA_TYPE_OBJECT
            elif isinstance(param_type, list) or isinstance(param_type, tuple) :
                param.type = DATA_TYPE_ARRAY
            elif param_type in BinaryFormatter.__json_type_map__ :
                param.type = BinaryFormatter.__json_type_map__[param_type]
            else :
                raise BinaryDeserializationError('JSON parameter {0} has unsupported type {1}.'.format(param_name, param_type))
            # Apply parameter type qualifier if neccessary. For basic type qualifier would be equal to None
            if param.type == DATA_TYPE_OBJECT :
                param.qualifier = BinaryFormatter.deserialize_json_object_definition(param_type)
            elif param.type == DATA_TYPE_ARRAY :
                param.qualifier = BinaryFormatter.deserialize_json_array_definition(param_type)
            else :
                param.qualifier = None
            res.append(param)
        return res
    
    @staticmethod
    def deserialize_register2(str_payload):
        """
        Method is dedicated to register2 payload. This code should not be used anywhere else.
        """
        def _deserialize_register2(val) :
            obj = RegistrationPayload()
            if 'id' in val :
                obj.device_id = uuid.UUID(val['id'])
            if 'key' in val :
                obj.device_key = val['key']
            if 'name' in val :
                obj.device_name = val['name']
            if 'deviceClass' in val and isinstance(val['deviceClass'], dict) :
                if 'name' in val['deviceClass'] :
                    obj.device_class_name = val['deviceClass']['name']
                if 'version' in val['deviceClass'] :
                    obj.device_class_version = val['deviceClass']['version']
            if 'equipment' in val and isinstance(val['equipment'], Iterable) :
                eqlst = []
                for eqval in val['equipment'] :
                    eqobj = Equipment()
                    if 'name' in eqval :
                        eqobj.name = eqval['name']
                    if 'code' in eqval :
                        eqobj.code = eqval['code']
                    if 'type' in eqval :
                        eqobj.typename = eqval['type']
                    eqlst.append(eqobj)
                obj.equipment = eqlst
            if 'commands' in val and isinstance(val['commands'], Iterable) :
                cmdlst = []
                for cmdval in val['commands'] :
                    cmdobj = Command()
                    if 'intent' in cmdval :
                        cmdobj.intent = int(cmdval['intent'])
                    if 'name' in cmdval :
                        cmdobj.name = cmdval['name']
                    if 'params' in cmdval and isinstance(cmdval['params'], dict) :
                        cmdobj.parameters = BinaryFormatter.deserialize_json_parameters(cmdval['params'])
                    cmdlst.append(cmdobj)
                obj.commands = cmdlst
            if 'notifications' in val and isinstance(val['notifications'], Iterable) :
                noflst = []
                for nofval in val['notifications'] :
                    nofobj = Notification()
                    if 'intent' in nofval :
                        nofobj.intent = int(nofval['intent'])
                    if 'name' in nofval :
                        nofobj.name = nofval['name']
                    if 'params' in nofval and isinstance(nofval['params'], dict) :
                        nofobj.parameters = BinaryFormatter.deserialize_json_parameters(nofval['params'])
                    noflst.append(nofobj)
                obj.notifications = noflst
            return obj
        val = json.loads(str_payload)
        return _deserialize_register2(val)


class BinaryConstructable(object):
    """
    This class states that subclass contains some metadata which could be used to produce
    binary data descriptor.
    """
    
    def __descriptor_counter() :
        i = 0
        while True :
            yield 'Descriptor{0}Class'.format(i)
            i += 1
    __descriptor_counter = __descriptor_counter()
    
    def descriptor_data(self):
        """
        Method should be overridden in a subclass.
        """
        raise NotImplementedError()
    
    def descriptor(self):
        data = self.descriptor_data()
        
        if not (isinstance(data, tuple) or isinstance(data, list)) :
            raise TypeError('Method descriptor_data should returns a TUPLE or a LIST')
        
        members = {'__binary_struct__': []}
        for field in data :
            fieldname = field.name
            fieldtype = field.type
            prop = None
            if fieldtype == DATA_TYPE_ARRAY :
                prop = array_binary_property(field.qualifier)
            elif fieldtype == DATA_TYPE_OBJECT :
                prop = object_binary_property(field.qualifier)
            else :
                prop = binary_property(fieldtype)
            members[fieldname] = prop
            members['__binary_struct__'].append(prop)
        return type(BinaryConstructable.__descriptor_counter.next(), (object,), members)


def define_accessors(field):
    def fget(self):
        return getattr(self, field)
    def fset(self, value):
        setattr(self, field, value)
    return (fget, fset)


class Parameter(object) :
    def __init__(self, type = DATA_TYPE_NULL, name = '') :
        self._type = type
        self._name = name
        self._qualifier = None
    
    def qualifier() :
        """
        Qualifier holds complex data structure description. It is not used directly during serialization rather
        it is used during auto-class-generation.
        """
        def fget(self) :
            return self._qualifier
        def fset(self, value) :
            self._qualifier = value
        return locals()
    qualifier = property(**qualifier())
    
    type = binary_property(DATA_TYPE_BYTE, *define_accessors('_type'))
    
    name = binary_property(DATA_TYPE_STRING, *define_accessors('_name'))
    
    __binary_struct__ = (type, name)


class Equipment(object):
    def __init__(self, name = '', code = 0, typename = ''):
        self._name = name
        self._code = code
        self._typename = typename
    
    name = binary_property(DATA_TYPE_STRING, *define_accessors('_name'))
    
    code = binary_property(DATA_TYPE_STRING, *define_accessors('_code'))
    
    typename = binary_property(DATA_TYPE_STRING, *define_accessors('_typename'))
    
    __binary_struct__ = (name, code, typename)


class Notification(object):
    def __init__(self, intent = 0, name = '', parameters = list()):
        self._intent = intent
        self._name = name
        self._parameters = parameters
    
    intent = binary_property(DATA_TYPE_WORD, *define_accessors('_intent'))
    
    name = binary_property(DATA_TYPE_STRING, *define_accessors('_name'))
    
    parameters = array_binary_property(Parameter, *define_accessors('_parameters'))
    
    __binary_struct__ = (intent, name, parameters)
    
    def descriptor_data(self) :
        return self._parameters


class Command(object):
    def __init__(self, intent = 0, name = '', parameters = list()):
        self._intent = intent
        self._name = name
        self._parameters = parameters
    
    intent = binary_property(DATA_TYPE_WORD, *define_accessors('_intent'))
    
    name = binary_property(DATA_TYPE_STRING, *define_accessors('_name'))
    
    parameters = array_binary_property(Parameter, *define_accessors('_parameters'))
    
    __binary_struct__ = (intent, name, parameters)
    
    def descriptor_data(self) :
        return self._parameters


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
    
    device_id = binary_property(DATA_TYPE_GUID, *define_accessors('_device_id'))
    
    device_key = binary_property(DATA_TYPE_STRING, *define_accessors('_device_key'))
    
    device_name = binary_property(DATA_TYPE_STRING, *define_accessors('_device_name'))
    
    device_class_name = binary_property(DATA_TYPE_STRING, *define_accessors('_device_class_name'))
    
    device_class_version = binary_property(DATA_TYPE_STRING, *define_accessors('_device_class_version'))
    
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
    
    command_id = binary_property(DATA_TYPE_DWORD, *define_accessors('_command_id'))
    
    status = binary_property(DATA_TYPE_STRING, *define_accessors('_status'))
    
    result = binary_property(DATA_TYPE_STRING, *define_accessors('_result'))
    
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
        return Protocol.connectionLost(self, reason)
    
    def makeConnection(self, transport):
        return Protocol.makeConnection(self, transport)
    
    def send_command(self, intent, payload):
        """
        Sends binary data into transport channel
        """
        msg = Packet(PACKET_SIGNATURE, 1, 0, intent, payload)
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
    TODO: get rid of this class
    """
    def _generate_binary_property(self, paramtype, fieldname):
        def getter(self):
            return getattr(self, fieldname)
        def setter(self, value):
            setattr(self, fieldname, value)
        return binary_property(paramtype, fget = getter, fset = setter)
    
    def generate(self, command):
        members = {'__binary_struct__': []}
        for param in command.parameters :
            fieldname = '_{0}'.format(param.name)
            paramtype = param.type
            if paramtype == DATA_TYPE_ARRAY :
                raise NotImplementedError('Array properties in automatic classes are not supported.')
            else :
                members[fieldname]  = None
                members[param.name] = prop = self._generate_binary_property(param.type, fieldname)
                members['__binary_struct__'].append(prop)
        return type('{0}Class'.format(command.name), (object,), members)


def binary_object_update(obj, value):
    """
    Applies dictionary values to corresponding object properties.
    @param value - should be a dictionary
    """
    props = [(prop[0], value[prop[1]]) for prop in [(getattr(obj.__class__, pname), pname) for pname in dir(obj.__class__)]
                                            if isinstance(prop[0], AbstractBinaryProperty) and
                                            prop[0] in obj.__binary_struct__ and
                                            value.has_key(prop[1])]
    for prop in props :
        if isinstance(prop[0], array_binary_property) :
            lst = []
            for i in prop[1] :
                element = prop[0].qualifier()
                binary_object_update(element, i)
                lst.append(element)
            prop[0].__set__(obj, lst)
        else :
            prop[0].__set__(obj, prop[1])
    return obj


def binary_object_to_dict(obj):
    props = [(prop[0], prop[1]) for prop in [(getattr(obj.__class__, pname), pname) for pname in dir(obj.__class__)]
                                            if isinstance(prop[0], AbstractBinaryProperty) and
                                            prop[0] in obj.__binary_struct__]
    result = {}
    for prop in props :
        if isinstance(prop[0], array_binary_property) :
            lst = []
            for o in prop[0].__get__(obj) :
                lst.append(binary_object_to_dict(o))
            result[prop[1]] = lst
        else :
            result[prop[1]] = prop[0].__get__(obj)
    return result


class BinaryFactory(ServerFactory):
    class _DeviceInfo(object):
        implements(IDeviceInfo)
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
        def __str__(self):
            return '{{device_id: "{0}", device_key: "{1}", network_name: "{2}", ... }}'.format(self.device_id, self.device_key, self.network_name)
    
    class _Notification(object):
        implements(INotification)
        def __init__(self, name, parameters):
            self.name = name
            self.parameters = parameters
        def __str__(self):
            return '{{name: "{0}", parameters: {1}}}'.format(self.name, self.parameters)
    
    class _DescrItem(object):
        def __init__(self, intent = 0, cls = None, info = None):
            self.intent = intent
            self.cls = cls
            self.info = info
    
    def __init__(self, gateway):
        self.packet_buffer = BinaryPacketBuffer()
        self.protocol = None
        self.gateway = gateway
        self.command_descriptors = {}
        self.notification_descriptors = {}
        self.pending_results = {}
    
    def register_command_descriptor(self, command_name, binary_class):
        """
        Method is specific for binary protocol. It allows specify custom deserialization
        description for the command's payload.
        """
        self.command_descriptors[command_name] = BinaryFactory._DescrItem(intent = -1, cls = binary_class)
    
    def register_notification_descriptor(self, notification_name, binary_class):
        self.notification_descriptors[notification_name] = BinaryFactory._DescrItem(intent = -1, cls = binary_class)
    
    def handle_registration_received(self, reg):
        """
        Adds command to binary-serializable-class mapping and then
        calls deferred object.
        """
        info = BinaryFactory._DeviceInfo(device_id = str(reg.device_id), \
                                device_key = reg.device_key, \
                                device_name = reg.device_name, \
                                device_status = 'Online', \
                                devcls_name = reg.device_class_name, \
                                devcls_version = reg.device_class_version, \
                                equipment = [devicehive.Equipment(e.name, e.code, e.typename) for e in reg.equipment])
        #
        autoclass_factory = AutoClassFactory()
        for command in reg.commands:
            if not command.name in self.command_descriptors :
                cls = autoclass_factory.generate(command)
                self.command_descriptors[command.name] = BinaryFactory._DescrItem(command.intent, cls, info)
            else :
                self.command_descriptors[command.name].intent = command.intent
                self.command_descriptors[command.name].info = command.info
        for notification in reg.notifications :
            if not notification.name in self.notification_descriptors :
                cls = autoclass_factory.generate(notification)
                self.notification_descriptors[notification.name] = BinaryFactory._DescrItem(notification.intent, cls, info)
            else :
                self.notification_descriptors[notification.name].intent = notification.intent
                self.notification_descriptors[notification.name].info = info
        self.gateway.registration_received(info)
    
    def handle_notification_command_result(self, notification):
        """
        Run all callbacks attached to notification_reveived deferred
        """
        log.msg('BinaryFactory.handle_notification_command_result')
        if notification.command_id in self.pending_results :
            deferred = self.pending_results.pop(notification.command_id)
            deferred.callback(devicehive.CommandResult(notification.status, notification.result))
    
    def handle_pass_notification(self, pkt):
        for (notif,nname) in [(self.notification_descriptors[nname], nname) for nname in self.notification_descriptors if self.notification_descriptors[nname].intent == pkt.intent] :
            obj = BinaryFormatter.deserialize(pkt.data, notif.cls)
            params = binary_object_to_dict(obj)
            self.gateway.notification_received(notif.info, BinaryFactory._Notification(nname, params))
    
    def packet_received(self, packet):
        log.msg('Data packet {0} has been received from device channel'.format(packet))
        if packet.intent == SYS_INTENT_REGISTER :
            regreq = BinaryFormatter.deserialize(packet.data, RegistrationPayload)
            self.handle_registration_received(regreq)
        elif packet.intent == SYS_INTENT_REGISTER2:
            pass
        elif packet.intent == SYS_INTENT_NOTIFY_COMMAND_RESULT :
            notifreq = BinaryFormatter.deserialize(packet.data, NotificationCommandResultPayload)
            self.handle_notification_command_result(notifreq)
        else:
            self.handle_pass_notification(packet)
    
    def do_command(self, command, finish_deferred):
        """
        This handler is called when a new command comes from DeviceHive server
        """
        log.msg('BinaryFactory.do_command')
        command_id = command['id']
        command_name = command['command']
        parameters = command['parameters']
        if command_name in self.command_descriptors :
            command_desc = self.command_descriptors[command_name]
            command_obj = command_desc.cls()
            autoclass_update_properties(command_obj, parameters)
            self.pending_results[command_id] = finish_deferred
            #
            self.protocol.send_command(command_desc.intent, command_bin)
        else :
            finish_deferred.errback()
    
    def buildProtocol(self, addr):
        log.msg('BinaryFactory.buildProtocol')
        self.protocol = BinaryProtocol(self) 
        return self.protocol


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
        return SerialPort(proto, self._port_addr.port, self._reactor, **self._port_addr.port_options)


