# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

"""
    Remove ugly 'top_level' property and use Command.parameter.value(binary_property) to
    unify the way how object, array and scalar parameters are stored.
    
    For now it is impossible to do this because We need to support both json and binary
    registration.
"""

import struct
import array
import uuid
# import json
from collections import Iterable, OrderedDict
from zope.interface import implements
from twisted.internet import interfaces
from twisted.python import log
from twisted.internet.protocol import ServerFactory, Protocol
from twisted.internet.serialport import SerialPort

import devicehive.dhjson
from devicehive import CommandResult, DeviceInfo as CDeviceInfo, DeviceClass as CDeviceClass, Equipment as CEquipment, Notification as CNotification
from devicehive.gateway import IGateway


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
    
    data = property(fget = lambda self : b'')
    
    def __len__(self):
        return self.length
    
    def checksum():
        """
        Checksum should be computed using all packet data.
        """
        def fget(self):
            s = ((self.signature & 0xff00) >> 8) + \
                (self.signature & 0xff) + \
                self.version + \
                self.flags + \
                ((self.length & 0xff00) >> 8) + \
                (self.length & 0xff) + \
                ((self.intent & 0xff00) >> 8) + \
                (self.intent & 0xff)
            if isinstance(self.data, str) :
                s += sum([ord(x) for x in self.data])
            else :
                s += sum(self.data)
            return (0xff - (s & 0xff)) & 0xff
        return locals()
    checksum = property(**checksum())
    
    def to_binary(self):
        _len  = self.length
        _data = [x for x in self.data]
        _intent = self.intent
        res = bytearray([((self.signature & 0xff00) >> 8) & 0xff,
                    self.signature & 0xff,
                    self.version & 0xff,
                    self.flags & 0xff,
                    _len & 0xff, ((_len & 0xff00) >> 8),
                    _intent & 0xff, ((_intent & 0xff00) >> 8)] + _data + [self.checksum,])
        return str(res)


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
        signature = struct.unpack_from('!H', binstr, min(PACKET_OFFSET_SIGN_LSB, PACKET_OFFSET_SIGN_MSB))[0]
        if signature != PACKET_SIGNATURE :
            raise InvalidSignatureError()
        version = ord(binstr[PACKET_OFFSET_VERSION])
        flags   = ord(binstr[PACKET_OFFSET_FLAGS])
        payload_len = struct.unpack_from('<H', binstr, min(PACKET_OFFSET_LEN_MSB, PACKET_OFFSET_LEN_LSB))[0]
        if binstr_len < (EMPTY_PACKET_LENGTH + payload_len) :
            raise InvalidPacketLengthError()
        intent = struct.unpack_from('<H', binstr, min(PACKET_OFFSET_INTENT_MSB, PACKET_OFFSET_INTENT_LSB))[0]
        frame_data = str(bytearray(binstr[PACKET_OFFSET_DATA:(PACKET_OFFSET_DATA + payload_len)]))
        if 0xff != (sum([ord(i) for i in binstr[0: PACKET_OFFSET_DATA + payload_len + 1]]) & 0xff) :
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
        self._data = b''
    
    data = property(fget = lambda self : self._data)
    
    def append(self, value):
        if isinstance(value, str) :
            self._data += value
        elif isinstance(value, tuple) or isinstance(value, list) :
            self._data += b''.join([chr(i) for i in value])
        else :
            self._data += value
        self._skip_to_next_packet()
    
    def _skip_to_next_packet(self):
        data_len = len(self._data)
        if data_len > 1:
            # this line is not neccessary but i think this would be better than deleting void list (del _data[:0])
            if self._data[0] == chr(PACKET_SIGNATURE_HI) and self._data[1] == chr(PACKET_SIGNATURE_LO) :
                return
            idx = -1
            try:
                idx = self._data.index(chr(PACKET_SIGNATURE_HI))
                if idx == data_len - 1 :
                    self._data = self._data[idx:]
                elif idx < data_len - 2 :
                    if self._data[idx + 1] == chr(PACKET_SIGNATURE_LO) :
                        self._data = self._data[idx:]
                    else :
                        self._data = self._data[idx + 1:]
                        self._skip_to_next_packet()
            except ValueError:
                self._data = b''
        elif data_len == 1 and self._data[0] != chr(PACKET_SIGNATURE_HI) :
            self._data = b''
    
    def has_packet(self):
        """
        Determines whether the buffer contains a complete packet
        """
        data_len = len(self._data)
        if data_len < EMPTY_PACKET_LENGTH :
            return False
        payload_len = struct.unpack_from('<H', self._data, min(PACKET_OFFSET_LEN_MSB, PACKET_OFFSET_LEN_LSB))[0]
        if data_len < payload_len + EMPTY_PACKET_LENGTH:
            return False
        return True
    
    def clear(self):
        self._data = b''
    
    def pop_packet(self):
        """
        Returns first received packet and then removes it from the buffer
        """
        if not self.has_packet() :
            return None
        pkt = Packet.from_binary(self._data)
        self._data = self._data[PACKET_OFFSET_DATA + 1 + ((( ord(self._data[PACKET_OFFSET_LEN_MSB]) << 8) & 0xff00) | ( ord(self._data[PACKET_OFFSET_LEN_LSB]) & 0xff)):]
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
                         DATA_TYPE_ARRAY: [],
                         DATA_TYPE_OBJECT: None}
    
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


class ArrayContainer(object):
    """
    Object of this type is used to store array of data and metadata which describes
        type of elements of this array.
    """
    
    def __init__(self, data_type, data = [], fget = None, fset = None):
        self.array = array_binary_property(data_type, fget, fset)
        self.array.__set__(self, data)
    
    def __getitem__(self, key) :
        return self.array.__get__(self).__getitem__(key)
    
    def __setitem__(self, key, value) :
        self.array.__get__(self).__setitem__(key, value)
    
    def __len__(self):
        return len(self.array.__get__(self))


class ArrayQualifier(object):
    """
    Specify type of elemets in array
    """
    __basic_types__ = (DATA_TYPE_NULL, DATA_TYPE_BYTE, DATA_TYPE_WORD, DATA_TYPE_DWORD, DATA_TYPE_QWORD, DATA_TYPE_SBYTE,
                       DATA_TYPE_SWORD, DATA_TYPE_SDWORD, DATA_TYPE_SQWORD, DATA_TYPE_SINGLE, DATA_TYPE_DOUBLE,
                       DATA_TYPE_BOOL, DATA_TYPE_GUID, DATA_TYPE_STRING, DATA_TYPE_BINARY)
    
    def __init__(self, data_type) :
        self.data_type = data_type
    
    def is_basic(self) :
        return any([bt == self.data_type for bt in ArrayQualifier.__basic_types__])
    
    def is_array(self) :
        return isinstance(self.data_type, ArrayQualifier)
    
    def is_object(self) :
        return (not self.is_basic()) and (not self.is_array())


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
    def serialize_scalar(type, value):
        result = bytearray()
        if type == DATA_TYPE_NULL :
            pass
        elif type in BinaryFormatter.__basic_type_map__ :
            packstr = BinaryFormatter.__basic_type_map__[type][0]
            result.extend(struct.pack(packstr, value))
        elif type == DATA_TYPE_GUID :
            if isinstance(value, uuid.UUID) :
                value = value.bytes
            elif len(value) != 16 :
                raise BinarySerializationError('guid property should of uuid.UUID type or be an array of 16 elements')
            result.extend(value)
        elif type == DATA_TYPE_STRING :
            bstr = array.array('B', value.encode('utf-8'))
            bstr_len = len(bstr)
            result.extend(struct.pack('<H', bstr_len))
            result.extend(bstr)
        elif type == DATA_TYPE_BINARY :
            str_len = len(value)
            result.extend(struct.pack('<H', str_len))
            result.extend(value)
        else :
            BinarySerializationError('unsupported property basic type {0} <{1} = {2}>'.format(type, type(value), value))
        return result
    
    @staticmethod
    def serialize_array(array_qualifier, value):
        result = bytearray()
        result.extend(struct.pack('<H', len(value)))
        if array_qualifier.is_basic() :
            for i in value :
                result.extend(BinaryFormatter.serialize_scalar(array_qualifier.data_type, i))
        elif array_qualifier.is_array() :
            sub_array_qualifier = array_qualifier.data_type
            for a in value :
                result.extend(BinaryFormatter.serialize_array(sub_array_qualifier, a.array.__get__(a)))
        else :
            for o in value :
                result.extend(BinaryFormatter.serialize_object(o))
        return result
    
    @staticmethod
    def serialize_object(obj) :
        if not hasattr(obj, '__binary_struct__') :
            raise BinarySerializationError('object {0} does not have conform to __binary_struct__ protocol'.format(obj))
        result = bytearray()
        for prop in obj.__binary_struct__ :
            if prop.type == DATA_TYPE_OBJECT :
                result.extend(BinaryFormatter.serialize(prop.__get__(obj)))
            elif prop.type == DATA_TYPE_ARRAY :
                result.extend(BinaryFormatter.serialize_array(prop.qualifier, prop.__get__(obj)))
            elif isinstance(prop, binary_property) :
                result.extend(BinaryFormatter.serialize_scalar(prop.type, prop.__get__(obj)))
            else :
                raise BinarySerializationError('unsupported property type {0}'.format(type(prop)))
        return result
    
    @staticmethod
    def serialize(value) :
        """
        Serializes object, array or scalar type into binary form.
        Is it much better to call concrete serialize_* method directly rather call this one.
        """
        if isinstance(value, list) or isinstance(value, tuple) :
            result = bytearray()
            for i in value :
                result.extend(BinaryFormatter.serialize(i))
            return result
        elif hasattr(value, '__binary_struct__') :
            return BinaryFormatter.serialize_object(value)
        else :
            return BinaryFormatter.serialize_scalar(DATA_TYPE_STRING, str(value))
    
    @staticmethod
    def deserialize_scalar(data, offset, type) :
        if type in BinaryFormatter.__basic_type_map__ :
            packstr, datalen = BinaryFormatter.__basic_type_map__[type]
            value = struct.unpack_from(packstr, data, offset)[0]
            offset += datalen
            return (value, offset)
        elif type == DATA_TYPE_GUID :
            value = struct.unpack_from('B' * 16, data, offset)
            fields = ((value[0] << 24) | (value[1] << 16) | (value[2] << 8) | (value[3]),
             (value[4] << 8) | value[5], (value[6] << 8) | value[7], value[8], value[9], (value[10] << 40) | (value[11] << 32) | (value[12] << 24) | (value[13] << 16) | (value[14] << 8) | value[15])
            offset += 16
            return (uuid.UUID(fields = fields), offset)
        elif type == DATA_TYPE_STRING :
            strlen = struct.unpack_from('<H', data, offset)[0]
            offset += 2
            bstr = bytearray(data[offset:offset + strlen])
            offset += strlen
            return (bstr.decode('utf-8'), offset)
        elif type == DATA_TYPE_BINARY :
            binlen = struct.unpack_from('<H', data, offset)[0]
            offset += 2
            bin = data[offset:offset + binlen]
            offset += binlen
            return (bin, offset)
        else :
            raise BinaryDeserializationError("unsupported scalar type {0}", type)
    
    @staticmethod
    def deserialize_array(data, offset, array_qualifier) :
        arrlen = struct.unpack_from('<H', data, offset)[0]
        offset += 2
        value = []
        if array_qualifier.is_basic() :
            for i in range(arrlen) :
                val, offset = BinaryFormatter.deserialize_scalar(data, offset, array_qualifier.data_type)
                value.append(val)
        elif array_qualifier.is_array() :
            for i in range(arrlen) :
                val, offset = BinaryFormatter.deserialize_array(data, offset, array_qualifier.data_type)
                value.append(val)
        else :
            for i in range(arrlen) :
                val, offset = BinaryFormatter.deserialize_object(data, offset, array_qualifier.data_type)
                value.append(val)
        return (value, offset)
    
    @staticmethod
    def deserialize_object(data, offset, cls) :
        if hasattr(cls, '__binary_struct__') :
            obj = cls()
            for prop in obj.__binary_struct__ :
                if prop.type == DATA_TYPE_NULL :
                    pass
                if (prop.type in BinaryFormatter.__basic_type_map__) or (prop.type == DATA_TYPE_GUID) or (prop.type == DATA_TYPE_STRING) or (prop.type == DATA_TYPE_BINARY) :
                    value, offset = BinaryFormatter.deserialize_scalar(data, offset, prop.type)
                    prop.__set__(obj, value)
                elif prop.type == DATA_TYPE_OBJECT and isinstance(prop, object_binary_property) :
                    subobj, offset = _deserialize(data, prop.qualifier, offset)
                    prop.__set__(obj, subobj)
                elif prop.type == DATA_TYPE_ARRAY and isinstance(prop, array_binary_property) :
                    value, offset = BinaryFormatter.deserialize_array(data, offset, prop.qualifier)
                    prop.__set__(obj, value)
                else :
                    raise BinaryDeserializationError('unsupported property type {0}'.format(type(prop)))
            return (obj, offset)
        else :
            raise BinaryDeserializationError('unsupported type {0}'.format(cls))
    
    @staticmethod
    def deserialize(data, cls):
        """
        Deserilizes @data array into object of type @type
        @param data - binary string/constant byte array/tuple or list
        @type  type - type in which binary string would be deserialized
        """
        data = array.array('B', data)
        obj, offset = BinaryFormatter.deserialize_object(data, 0, cls)
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
            return ArrayQualifier(BinaryFormatter.deserialize_json_object_definition(etype))
        elif (isinstance(etype, tuple) or isinstance(etype, list)) and len(etype) == 1 :
            return ArrayQualifier(BinaryFormatter.deserialize_json_array_definition(etype))
        elif etype in BinaryFormatter.__json_type_map__ :
            return ArrayQualifier(BinaryFormatter.__json_type_map__[etype])
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
    def deserialize_json_parameter(param_type, param_name = ''):
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
        return param
    
    @staticmethod
    def deserialize_json_array_parameter(param_type, param_name):
        param = Parameter()
        param.name = param_name
        param.type = DATA_TYPE_ARRAY
        param.qualifier = BinaryFormatter.deserialize_json_array_definition(param_type)
        return [param]
    
    @staticmethod
    def deserialize_json_parameters(params) :
        """
        Method converts list of json parameter definitions into BinarySerializable structure
        """
        res = []
        for param_name in params :
            param_type = params[param_name]
            res.append(BinaryFormatter.deserialize_json_parameter(param_type, param_name))
        return res
    
    @staticmethod
    def deserialize_register2(str_payload):
        """
        Method is dedicated to register2 payload. This code should not be used anywhere else.
        """
        log.msg('Deserializing registration 2 message {0}.'.format(str_payload))
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
                    if 'params' in cmdval :
                        if isinstance(cmdval['params'], dict) :
                            cmdobj.parameters = BinaryFormatter.deserialize_json_parameters(cmdval['params'])
                        elif (isinstance(cmdval['params'], list) or isinstance(cmdval['params'], tuple)) and len(cmdval['params']) == 1 :
                            cmdobj.parameters = BinaryFormatter.deserialize_json_array_parameter(cmdval['params'], 'top_level')
                        else :
                            cmdobj.parameters = [BinaryFormatter.deserialize_json_parameter(cmdval['params'], 'top_level')]
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
                    if 'params' in nofval :
                        if isinstance(nofval['params'], dict) :
                            nofobj.parameters = BinaryFormatter.deserialize_json_parameters(nofval['params'])
                        elif (isinstance(nofval['params'], list) or isinstance(nofval['params'], tuple)) and len(nofval['params']) == 1 :
                            nofobj.parameters = BinaryFormatter.deserialize_json_array_parameter(nofval['params'], 'top_level')
                        else :
                            nofobj.parameters = [BinaryFormatter.deserialize_json_parameter(nofval['params'], 'top_level')]
                    noflst.append(nofobj)
                obj.notifications = noflst
            return obj
        #val = json.JSONDecoder(object_pairs_hook=OrderedDict).decode(str_payload)
        parser = devicehive.dhjson.Parser(str_payload)
        val = parser.parse()
        return _deserialize_register2(val)


class ToDictionary(object):
    """
    Converts binary serializable class into dictionary
    """
    
    def to_dict(self) :
        def _to_dict(obj) :
            def _array_to_dict(obj, prop) :
                lst = []
                if prop.qualifier.is_basic() :
                    for o in prop.__get__(obj) :
                        lst.append(o)
                elif prop.qualifier.is_array() :
                    items = prop.__get__(obj)
                    if not all([isinstance(o, ArrayContainer) for o in items if not o is None]) :
                        raise BinaryDeserializationError('Elements of sub array should be of ArrayContainer type')
                    for o in [item for item in items if not item is None] :
                        if o.array.qualifier.data_type != prop.qualifier.data_type.data_type :
                            raise BinaryDeserializationError('Element type {0} is not consistent with property type {1}.'.format(o.array.qualifier, prop.qualifier.data_type))
                        lst.append( _array_to_dict(o, o.array) )
                else :
                    for o in prop.__get__(obj) :
                        lst.append(_to_dict(o))
                return lst
            props = [(prop[0], prop[1]) for prop in [(getattr(obj.__class__, pname), pname) for pname in dir(obj.__class__)]
                                                    if isinstance(prop[0], AbstractBinaryProperty) and prop[0] in obj.__binary_struct__]
            res = {}
            for i in props :
                prop, propname = i
                if isinstance(prop, object_binary_property) :
                    subo = prop.__get__(obj)
                    if not subo is None :
                        res[propname] = _to_dict( subo )
                elif isinstance(prop, array_binary_property) :
                    if prop.qualifier.data_type != DATA_TYPE_NULL :
                        res[propname] = _array_to_dict(obj, prop)
                elif isinstance(prop, binary_property) :
                    res[propname] = prop.__get__(obj)
                else :
                    raise TypeError('Unsupported type.')
            return res
        res = _to_dict(self)
        if (len(res) == 1) and 'top_level' in res :
            res = res['top_level']
        return res


class Updateable(object):
    """
    Updates binary serializable object from supplied json dictionary.
    """
    
    @staticmethod
    def update_array (array_qualifier, value) :
        if array_qualifier.is_basic() :
            return list(value)
        elif array_qualifier.is_array() :
            lst = []
            subqualifier = array_qualifier.data_type
            for i in value :
                lst.append(ArrayContainer(subqualifier, Updateable.update_array(subqualifier, i)))
            return lst
        elif array_qualifier.is_object() :
            lst = []
            for i in value :
                o = array_qualifier.data_type()
                Updateable.update_object(o, i)
                lst.append(o)
            return lst
    
    @staticmethod
    def update_object(obj, value) :
        if not isinstance(value, dict) :
            raise TypeError('Failed to update object {0}. Reason: value parameter must be of dict type, got {1}.'.format(obj, type(value)))
        
        cls = obj.__class__
        # iterate over AbstractBinaryProperties which names are present in value dictionary
        for prop, pname in [x for x in [(getattr(cls, pname), pname) for pname in dir(cls) if value.has_key(pname)] if isinstance(x[0], AbstractBinaryProperty) and x[0] in cls.__binary_struct__] :
            if prop.type == DATA_TYPE_OBJECT :
                o = prop.qualifier()
                Updateable.update_object(o, value[pname])
                prop.__set__(obj, o)
            elif prop.type == DATA_TYPE_ARRAY :
                prop.__set__(obj, Updateable.update_array(prop.qualifier, value[pname]))
            else :
                prop.__set__(obj, value[pname])
    
    def update(self, value) :
        """
        Updates object using values stored in value dictionary.
        
        Verification is neccessary because devicehive server may send and empty parameters list.
        In this case their default value will be sent.
        """
        if value is not None :
            if isinstance(value, dict) :
                Updateable.update_object(self, value)
            elif hasattr(self.__class__, 'top_level') :
                prop = getattr(self.__class__, 'top_level')
                if isinstance(prop, AbstractBinaryProperty) :
                    if isinstance(value, list) or isinstance(value, tuple) :
                        prop.__set__(self, Updateable.update_array(prop.qualifier, value))
                    else :
                        prop.__set__(self, value)
                    pass
                pass
            pass


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
        return type(BinaryConstructable.__descriptor_counter.next(), (ToDictionary, Updateable), members)


def define_accessors(field):
    def fget(self):
        return getattr(self, field)
    def fset(self, value):
        setattr(self, field, value)
    return (fget, fset)


class Parameter(object) :
    def __init__(self, type = DATA_TYPE_NULL, name = '', qualifier = None) :
        self._type = type
        self._name = name
        self._qualifier = qualifier
    
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


class Notification(BinaryConstructable):
    def __init__(self, intent = 0, name = '', parameters = list()):
        self._intent = intent
        self._name = name
        self._parameters = parameters
    
    def descriptor_data(self) :
        return self._parameters
    
    intent = binary_property(DATA_TYPE_WORD, *define_accessors('_intent'))
    
    name = binary_property(DATA_TYPE_STRING, *define_accessors('_name'))
    
    parameters = array_binary_property(ArrayQualifier(Parameter), *define_accessors('_parameters'))
    
    __binary_struct__ = (intent, name, parameters)


class Command(BinaryConstructable):
    def __init__(self, intent = 0, name = '', parameters = list()):
        self._intent = intent
        self._name = name
        self._parameters = parameters
    
    def descriptor_data(self) :
        return self._parameters
    
    intent = binary_property(DATA_TYPE_WORD, *define_accessors('_intent'))
    
    name = binary_property(DATA_TYPE_STRING, *define_accessors('_name'))
    
    parameters = array_binary_property( ArrayQualifier(Parameter), *define_accessors('_parameters'))
    
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
    
    device_id = binary_property(DATA_TYPE_GUID, *define_accessors('_device_id'))
    
    device_key = binary_property(DATA_TYPE_STRING, *define_accessors('_device_key'))
    
    device_name = binary_property(DATA_TYPE_STRING, *define_accessors('_device_name'))
    
    device_class_name = binary_property(DATA_TYPE_STRING, *define_accessors('_device_class_name'))
    
    device_class_version = binary_property(DATA_TYPE_STRING, *define_accessors('_device_class_version'))
    
    equipment = array_binary_property( ArrayQualifier(Equipment) )
    
    notifications = array_binary_property( ArrayQualifier(Notification) )
    
    commands = array_binary_property( ArrayQualifier(Command) )
    
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
        bin_pkt = msg.to_binary()
        log.msg('Sending packet "{0}" into transport.'.format(' '.join([hex(ord(x)) for x in bin_pkt])))
        self.transport.write(bin_pkt)
    
    def connectionMade(self):
        """
        Called when connection is made. Right after channel has been established gateway need to 
        send registration request intent to device(s).
        """
        pkt = RegistrationRequestPacket()
        self.transport.write(pkt.to_binary())


class BinaryFactory(ServerFactory):
    class _DescrItem(object):
        def __init__(self, intent = 0, name = None, cls = None, info = None):
            self.intent = intent
            self.name = name
            self.cls = cls
            self.info = info
    
    def __init__(self, gateway):
        self.packet_buffer = BinaryPacketBuffer()
        self.protocol = None
        self.gateway = gateway
        self.command_descriptors = {}
        self.notification_descriptors = {}
        self.pending_results = {}
    
    def handle_registration_received(self, reg):
        """
        Adds command to binary-serializable-class mapping and then
        calls deferred object.
        """
        info = CDeviceInfo(id = str(reg.device_id), \
                           key = reg.device_key, \
                           name = reg.device_name, \
                           device_class = CDeviceClass(name = reg.device_class_name, version = reg.device_class_version), \
                           equipment = [CEquipment(name = e.name, code = e.code, type = e.typename) for e in reg.equipment])
        def fill_descriptors(objs, out, info) :
            for obj in objs :
                okey = obj.intent
                if not okey in out :
                    cls = obj.descriptor()
                    out[okey] = BinaryFactory._DescrItem(obj.intent, obj.name, cls, info)
                else :
                    out[okey].intent = obj.intent
                    out[okey].name = obj.name
                    out[okey].info = info
        fill_descriptors(reg.commands, self.command_descriptors, info)
        fill_descriptors(reg.notifications, self.notification_descriptors, info)
        self.gateway.registration_received(info)
    
    def handle_notification_command_result(self, notification):
        """
        Run all callbacks attached to notification_received deferred
        """
        log.msg('BinaryFactory.handle_notification_command_result')
        if notification.command_id in self.pending_results :
            deferred = self.pending_results.pop(notification.command_id)
            deferred.callback(CommandResult(notification.status, notification.result))
    
    def handle_pass_notification(self, pkt):
        for notif in [self.notification_descriptors[intent] for intent in self.notification_descriptors if intent == pkt.intent] :
            obj = BinaryFormatter.deserialize(pkt.data, notif.cls)
            params = obj.to_dict()
            self.gateway.notification_received(notif.info, CNotification(notif.name, params))
    
    def packet_received(self, packet):
        log.msg('Data packet {0} has been received from device channel'.format(packet))
        if packet.intent == SYS_INTENT_REGISTER :
            regreq = BinaryFormatter.deserialize(packet.data, RegistrationPayload)
            self.handle_registration_received(regreq)
        elif packet.intent == SYS_INTENT_REGISTER2:
            regreq = BinaryFormatter.deserialize_register2(packet.data[2:])
            self.handle_registration_received(regreq)
        elif packet.intent == SYS_INTENT_NOTIFY_COMMAND_RESULT :
            notifreq = BinaryFormatter.deserialize(packet.data, NotificationCommandResultPayload)
            self.handle_notification_command_result(notifreq)
        else:
            self.handle_pass_notification(packet)
    
    def do_command(self, device_id, command, finish_deferred):
        """
        This handler is called when a new command comes from DeviceHive server.
        
        @type command: C{object}
        @param command: object which implements C{ICommand} interface
        """
        log.msg('A new command has came from a device-hive server to device "{0}".'.format(device_id))
        command_id = command.id
        command_name = command.command
        descrs = [x for x in self.command_descriptors.values() if x.name == command_name]
        if len(descrs) > 0 :
            log.msg('Has found {0} matching command {1} descriptor(s).'.format(len(descrs), command))
            command_desc = descrs[0]
            command_obj = command_desc.cls()
            log.msg('Command parameters {0}.'.format(command.parameters, type(command.parameters)))
            command_obj.update(command.parameters)
            self.pending_results[command_id] = finish_deferred
            self.protocol.send_command(command_desc.intent, struct.pack('<I', command_id) + BinaryFormatter.serialize_object(command_obj))
        else :
            msg = 'Command {0} is not registered for device "{1}".'.format(command, device_id)
            log.err(msg)
            finish_deferred.errback(msg)
    
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
