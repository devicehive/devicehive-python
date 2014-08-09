# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

import unittest

from twisted.test.proto_helpers import StringTransport

from devicehive.gateway.binary import *


class PacketTests(unittest.TestCase):
    def setUp(self):
        self.pkt = Packet(PACKET_SIGNATURE, 2, 3, 4, '123')
    
    def tearDown(self):
        pass
    
    def test_properties(self):
        self.assertEquals(PACKET_SIGNATURE, self.pkt.signature, 'Signatures are not equal')
        self.assertEquals(2, self.pkt.version, 'Versions are not equal')
        self.assertEquals(3, self.pkt.flags, 'Flags are not equal')
        self.assertEquals(4, self.pkt.intent, 'Intents are not equal')
    
    def test_checksum(self):
        self.assertEquals(0xd5, self.pkt.checksum, 'Invalid checksum')
    
    def test_checksum2(self):
        pkt =  Packet(PACKET_SIGNATURE, 0x1, 0x0, 0x101, b'\x01\x02\x03\x04\x05\x06')
        self.assertEquals(0x59, pkt.checksum)
    
    def test_to_binary(self):
        tstval = bytearray([PACKET_SIGNATURE_HI, PACKET_SIGNATURE_LO, 0x02, 0x03, 0x03, 0x00, 0x04, 0x00, 0x31, 0x32, 0x33, 0xd5])
        binval = self.pkt.to_binary()
        self.assertEquals(tstval, binval, 'Invalid binary message has been formated')
    
    def test_from_binary(self):
        pktcopy = Packet.from_binary(self.pkt.to_binary())
        self.assertEquals(self.pkt.signature, pktcopy.signature)
        self.assertEquals(self.pkt.version, pktcopy.version)
        self.assertEquals(self.pkt.flags, pktcopy.flags)
        self.assertEquals(self.pkt.intent, pktcopy.intent)
        self.assertEquals(self.pkt.length, pktcopy.length)
        self.assertEquals(self.pkt.data, pktcopy.data)

    def test_crc_error(self):
        tstval = bytearray([PACKET_SIGNATURE_HI, PACKET_SIGNATURE_LO, 0x02, 0x03, 0x03, 0x00, 0x04, 0x00, 0x31, 0x32, 0x33, 0xBA])
        try:
           Packet.from_binary( str(tstval) )
           self.assertTrue(False, 'from_binary method should raises InvalidCRCError')
        except InvalidCRCError:
            pass
    
    def test_incomplete_packet(self):
        tstval = bytearray([0, 1, 2, 3])
        try:
            Packet.from_binary( str(tstval) )
            self.assertTrue(False, 'from_binary method should raises IncompltePacketError in case data-packet passed into this method is too small')
        except IncompletePacketError:
            pass
    
    def test_invalid_packet_length(self):
        tstval = bytearray([PACKET_SIGNATURE_HI, PACKET_SIGNATURE_LO, 0x02, 0x03, 0x00, 0x03, 0x04, 0x00, 0x31, 0x32, 0x33, 0xd5])
        try:
            Packet.from_binary( str(tstval) )
            self.assertTrue(False, 'from_binary method should raises InvalidPacketlengthError in case there not enough data passed into it')
        except InvalidPacketLengthError:
            pass
    
    def test_raise_invalid_signature(self):
        tstval = bytearray([0xBA, 0xD1, 0x02, 0x03, 0x03, 0x00, 0x04, 0x00, 0x31, 0x32, 0x33, 0xd5])
        try:
            Packet.from_binary( str(tstval) )
            self.assertTrue(False, 'from_binary method should raises InvalidSignatureError in case packet signature is incorrect')
        except InvalidSignatureError:
            pass


class BinaryPacketBufferTests(unittest.TestCase):
    def test_adding_normal_packet(self):
        pkt = [PACKET_SIGNATURE_HI, PACKET_SIGNATURE_LO, 0x02, 0x03, 0x03, 0x00, 0x04, 0x00, 0x31, 0x32, 0x33, 0xd5]
        pkt_buff  = BinaryPacketBuffer()
        pkt_buff.append(pkt)
        self.assertEquals( str(bytearray(pkt)), pkt_buff.data)
        self.assertTrue(pkt_buff.has_packet())
    
    def test_adding_partial_packet(self):
        pkt = [PACKET_SIGNATURE_HI, PACKET_SIGNATURE_LO, 0x02, 0x03, 0x03, 0x00, 0x04, 0x00, 0x31, 0x32, 0x33, 0xd5]
        pkt_buff  = BinaryPacketBuffer()
        pkt_buff.append(pkt[:4])
        pkt_buff.append(pkt[4:])
        self.assertEquals( str(bytearray(pkt)), pkt_buff.data, 'One complete packet should be located in the buffer')
        self.assertTrue(pkt_buff.has_packet())
    
    def test_add_packet_prefixed_with_junk(self):
        pkt = [0xBA, 0xDB, 0xAD, PACKET_SIGNATURE_HI, PACKET_SIGNATURE_LO, 0x02, 0x03, 0x03, 0x00, 0x04, 0x00, 0x31, 0x32, 0x33, 0xd5]
        pkt_buff = BinaryPacketBuffer()
        pkt_buff.append(pkt[:6])
        pkt_buff.append(pkt[6:])
        self.assertEquals( str(bytearray(pkt[3:])), pkt_buff.data, 'Junk data should be skipped in the head of packet buffer. {0} != {1}'.format(pkt[3:], pkt_buff.data))
        self.assertTrue(pkt_buff.has_packet())

    def test_onechar_junk_add(self):
        pkt_buff = BinaryPacketBuffer()
        pkt_buff.append([0])
        pkt_buff.append([1])
        pkt_buff.append([2])
        self.assertEquals(0, len(pkt_buff.data), 'If buffer is empty and one character comes to it this character should be of SIGNATURE_HI value')
        self.assertFalse(pkt_buff.has_packet())

    def test_invalid_signature(self):
        pkt = [99, 98, 97, PACKET_SIGNATURE_HI, 96, PACKET_SIGNATURE_LO, 94, 93, PACKET_SIGNATURE_HI, PACKET_SIGNATURE_LO, 0x02, 0x03, 0x03, 0x00, 0x04, 0x00, 0x31, 0x32, 0x33, 0xd5]
        pkt_buff = BinaryPacketBuffer()
        pkt_buff.append(pkt)
        self.assertEquals( str(bytearray(pkt[8:])), pkt_buff.data, 'Buffer should starts from FULL frame signature')
        self.assertTrue(pkt_buff.has_packet())
    
    def test_inv_sign_last_signhi(self):
        pkt = [99, 98, 97, PACKET_SIGNATURE_HI, 96, PACKET_SIGNATURE_LO, 94, 93, PACKET_SIGNATURE_HI]
        pkt_buff = BinaryPacketBuffer()
        pkt_buff.append(pkt)
        self.assertEquals( str(bytearray([PACKET_SIGNATURE_HI])), pkt_buff.data, 'One last character should stay untoched if it is SIGNATURE_HI')
        self.assertFalse(pkt_buff.has_packet())
    
    def test_signature_byteatatime(self):
        pkt = [99, 98, 97, PACKET_SIGNATURE_HI, 96, PACKET_SIGNATURE_LO, 94, 93, PACKET_SIGNATURE_HI, PACKET_SIGNATURE_LO, 0x02, 0x03, 0x03, 0x00, 0x04, 0x00, 0x31, 0x32, 0x33, 0xd5]
        pkt_buff = BinaryPacketBuffer()
        for byte in pkt:
            pkt_buff.append([byte])
        self.assertEquals(str(bytearray(pkt[8:])), pkt_buff.data, 'Even if we adds packet by one byte the buffer should starts from FULL frame signature')
        self.assertTrue(pkt_buff.has_packet())


class _TestObject(object):
    class _SubObject(object):
        def __init__(self, val = 0):
            self._val = val
        def _set_val(self, value):
            self._val = value
        sword_prop = binary_property(DATA_TYPE_SWORD, fget = lambda self : self._val, fset = _set_val)
        __binary_struct__ = [sword_prop]
    
    def __init__(self):
        self._byte_prop = 0
        self._word_prop = 0
        self._dword_prop = 0
        self._bool_prop = False
        self._false_prop = False
        self._str_prop = ''
        self.arr_prop = []
        self.guid_prop = uuid.uuid1()
        self.aguid_prop = (uuid.uuid1()).bytes

    def gen_props(name):
        def fget(self):
            return getattr(self, name)

        def fset(self, value):
            setattr(self, name, value)
        return {'fget': fget, 'fset': fset}

    byte_prop = binary_property(DATA_TYPE_BYTE, **gen_props('_byte_prop'))
    word_prop = binary_property(DATA_TYPE_WORD, **gen_props('_word_prop'))
    dword_prop = binary_property(DATA_TYPE_DWORD, **gen_props('_dword_prop'))
    bool_prop = binary_property(DATA_TYPE_BOOL, **gen_props('_bool_prop'))
    false_prop = binary_property(DATA_TYPE_BOOL, **gen_props('_false_prop'))
    str_prop = binary_property(DATA_TYPE_STRING, **gen_props('_str_prop'))
    arr_prop = array_binary_property(ArrayQualifier(_SubObject), **gen_props('_arr_prop'))
    guid_prop = binary_property(DATA_TYPE_GUID, **gen_props('_guid_prop'))
    aguid_prop = binary_property(DATA_TYPE_GUID, **gen_props('_aguid_prop'))
    __binary_struct__ = (byte_prop, word_prop, dword_prop, bool_prop, false_prop, str_prop, arr_prop, guid_prop, aguid_prop)


class BinaryFormatterTest(unittest.TestCase):
    def _create_default_test_object(self):
        res = _TestObject()
        res.byte_prop  = 0xab
        res.word_prop  = 0xabcd
        res.dword_prop = 0x12345678
        res.bool_prop  = True
        res.false_prop = False
        res.str_prop   = 'abc'
        res.arr_prop   = (_TestObject._SubObject(-1024), _TestObject._SubObject(-8192))
        res.guid_prop  = uuid.UUID('fa8a9d6e-6555-11e2-89b8-e0cb4eb92129')
        res.aguid_prop = res.guid_prop.bytes
        return res
    
    def setUp(self):
        self.binary = bytearray([0xab,
                                 0xcd, 0xab,
                                 0x78, 0x56, 0x34, 0x12,
                                 0x01,
                                 0x00,
                                 0x03, 0x00, ord('a'), ord('b'), ord('c'),
                                 0x02, 0x00, 0x00, 0xfc, 0x00, 0xe0,
                                 0xfa, 0x8a, 0x9d, 0x6e, 0x65, 0x55, 0x11, 0xe2, 0x89, 0xb8, 0xe0, 0xcb, 0x4e, 0xb9, 0x21, 0x29,
                                 0xfa, 0x8a, 0x9d, 0x6e, 0x65, 0x55, 0x11, 0xe2, 0x89, 0xb8, 0xe0, 0xcb, 0x4e, 0xb9, 0x21, 0x29])
    
    def test_serialize_byte(self):
        obj = self._create_default_test_object()
        binstr = BinaryFormatter.serialize(obj)
        self.assertEquals(self.binary, binstr)
    
    def test_deserializer(self):
        res = BinaryFormatter.deserialize(self.binary, _TestObject)
        self.assertEquals(0xab, res.byte_prop)
        self.assertEquals(0xabcd, res.word_prop)
        self.assertEquals(0x12345678, res.dword_prop)
        self.assertTrue(res.bool_prop)
        self.assertFalse(res.false_prop)
        self.assertEquals('abc', res.str_prop)
        self.assertEquals(2, len(res.arr_prop))
        self.assertEquals(-1024, res.arr_prop[0].sword_prop)
        self.assertEquals(-8192, res.arr_prop[1].sword_prop)
        
        guid = uuid.UUID('fa8a9d6e-6555-11e2-89b8-e0cb4eb92129')
        self.assertEquals(guid, res.guid_prop)
        self.assertEquals(guid, res.aguid_prop)
    
    def test_deserialize_array_prop_invalid_definition(self):
        class _InvalidDefObject(object):
            def __init__(self, val = 0):
                self._val = val
            def _set_val(self, value):
                self._val = value
            invalid_array_prop = binary_property(DATA_TYPE_ARRAY, fget = lambda self : self._val, fset = _set_val)
            __binary_struct__ = [invalid_array_prop]
        invalidbin = bytearray([0x01, 0x00, 0xff])
        try :
            res = BinaryFormatter.deserialize(self.binary, _InvalidDefObject)
            self.assertTrue(False, 'Deserialization should raises an exception on attempt to deserialize invalid defined object')
        except BinaryDeserializationError:
            pass
    
    def test_deserialize_register2(self):
        payload = b'{"id":"fa8a9d6e-6555-11e2-89b8-e0cb4eb92129","key":"DEVICE_KEY","name":"DEVICE_NAME","deviceClass":{"name":"DEVICE_CLASS_NAME","version":"DEVICE_CLASS_VERSION"},"equipment":[{"code":"LED_EQP_CODE","name":"LED_EQP_NAME","type":"LED_EQP_TYPE"},{"code":"BTN_EQP_CODE","name":"BTN_EQP_NAME","type":"BTN_EQP_TYPE"}],"commands":[{"intent":257,"name":"UpdateLedState","params":{"equipment":"str","state":"bool"}}],"notifications":[{"intent":256,"name":"equipment","params":{"equipment":"str","state":"bool"}}]}'
        obj = BinaryFormatter.deserialize_register2(payload)
        self.assertEquals(uuid.UUID('fa8a9d6e-6555-11e2-89b8-e0cb4eb92129'), obj.device_id)
        self.assertEquals(u'DEVICE_KEY', obj.device_key)
        self.assertEquals(u'DEVICE_NAME', obj.device_name)
        self.assertEquals(u'DEVICE_CLASS_NAME', obj.device_class_name)
        self.assertEquals(u'DEVICE_CLASS_VERSION', obj.device_class_version)
        # equipment
        self.assertEquals(2, len(obj.equipment))
        self.assertEquals(u'LED_EQP_CODE', obj.equipment[0].code)
        self.assertEquals(u'LED_EQP_NAME', obj.equipment[0].name)
        self.assertEquals(u'LED_EQP_TYPE', obj.equipment[0].typename)
        self.assertEquals(u'BTN_EQP_CODE', obj.equipment[1].code)
        self.assertEquals(u'BTN_EQP_NAME', obj.equipment[1].name)
        self.assertEquals(u'BTN_EQP_TYPE', obj.equipment[1].typename)
        # command
        self.assertEquals(1, len(obj.commands))
        self.assertEquals(257, obj.commands[0].intent)
        self.assertEquals(u'UpdateLedState', obj.commands[0].name)
        self.assertEquals(2, len(obj.commands[0].parameters))
        self.assertEquals(u'equipment', obj.commands[0].parameters[0].name)
        self.assertEquals(DATA_TYPE_STRING, obj.commands[0].parameters[0].type)
        self.assertEquals(u'state', obj.commands[0].parameters[1].name)
        self.assertEquals(DATA_TYPE_BOOL, obj.commands[0].parameters[1].type)
        # notifications
        self.assertEquals(1, len(obj.notifications))
        self.assertEquals(256, obj.notifications[0].intent)
        self.assertEquals(u'equipment', obj.notifications[0].name)
        self.assertEquals(2, len(obj.notifications[0].parameters))
        self.assertEquals(u'equipment', obj.notifications[0].parameters[0].name)
        self.assertEquals(DATA_TYPE_STRING, obj.notifications[0].parameters[0].type)
        self.assertEquals(u'state', obj.notifications[0].parameters[1].name)
        self.assertEquals(DATA_TYPE_BOOL, obj.notifications[0].parameters[1].type)
    
    def test_deserialize_complex_array(self) :
        payload = b'{"id":"fa8a9d6e-6555-11e2-89b8-e0cb4eb92129","key":"1","name":"2","deviceClass":{"name":"3","version":"4"},"equipment":[{"code":"5","name":"6","type":"7"}],"commands":[{"intent":257,"name":"7","params":{"e":"str","state":"bool"}}],"notifications":[{"intent":300,"name":"equipment","params":{"array_prop":["str"]}}]}'
        obj = BinaryFormatter.deserialize_register2(payload)
        self.assertEquals(300, obj.notifications[0].intent)
        # test array property
        prop = obj.notifications[0].parameters[0]
        self.assertEquals(DATA_TYPE_ARRAY, prop.type)
        self.assertTrue(isinstance(prop.qualifier, ArrayQualifier))
        self.assertEquals(DATA_TYPE_STRING, prop.qualifier.data_type)
    
    def test_deserialize_complex_obj(self) :
        payload = b'{"id":"fa8a9d6e-6555-11e2-89b8-e0cb4eb92129","key":"1","name":"2","deviceClass":{"name":"3","version":"4"},"equipment":[{"code":"5","name":"6","type":"7"}],"commands":[{"intent":257,"name":"7","params":{"e":"str","state":"bool"}}],"notifications":[{"intent":300,"name":"equipment","params":{"obj_prop":{"str_prop":"str"}}}]}'
        obj = BinaryFormatter.deserialize_register2(payload)
        self.assertEquals(300, obj.notifications[0].intent)
        prop = obj.notifications[0].parameters[0]
        self.assertEquals(u'obj_prop', prop.name)
        self.assertEquals(DATA_TYPE_OBJECT, prop.type)
        self.assertTrue(hasattr(prop.qualifier, 'str_prop'))
        self.assertTrue(isinstance(prop.qualifier.str_prop, binary_property))
        self.assertEquals(DATA_TYPE_STRING, prop.qualifier.str_prop.type)
    
    def test_deserialize_complex_array_obj(self):
        payload = b'{"id":"fa8a9d6e-6555-11e2-89b8-e0cb4eb92129","key":"1","name":"2","deviceClass":{"name":"3","version":"4"},"equipment":[{"code":"5","name":"6","type":"7"}],"commands":[{"intent":257,"name":"7","params":{"e":"str","state":"bool"}}],"notifications":[{"intent":300,"name":"equipment","params":{"array_prop":[{"str_prop":"str"}]}}]}'
        obj = BinaryFormatter.deserialize_register2(payload)
        prop = obj.notifications[0].parameters[0]
        self.assertEquals(u'array_prop', prop.name)
        self.assertEquals(DATA_TYPE_ARRAY, prop.type)
        self.assertTrue( isinstance(prop.qualifier, ArrayQualifier) )
        self.assertFalse(prop.qualifier.data_type is None)
        self.assertTrue(hasattr(prop.qualifier.data_type, 'str_prop'))
        self.assertTrue(isinstance(prop.qualifier.data_type.str_prop, binary_property))
        self.assertEquals(DATA_TYPE_STRING, prop.qualifier.data_type.str_prop.type)
    
    def test_deserialize_complex_array_array_obj_array(self) :
        payload = b'{"id":"fa8a9d6e-6555-11e2-89b8-e0cb4eb92129","key":"1","name":"2","deviceClass":{"name":"3","version":"4"},"equipment":[{"code":"5","name":"6","type":"7"}],"commands":[{"intent":257,"name":"7","params":{"e":"str","state":"bool"}}],"notifications":[{"intent":300,"name":"equipment","params":{"array_prop":[[{"array_prop":["str"]}]]}}]}'
        obj = BinaryFormatter.deserialize_register2(payload)
        prop = obj.notifications[0].parameters[0]
        self.assertEquals(u'array_prop', prop.name)
        self.assertEquals(DATA_TYPE_ARRAY, prop.type)
        self.assertTrue(isinstance(prop.qualifier, ArrayQualifier))
        self.assertTrue(isinstance(prop.qualifier.data_type, ArrayQualifier))
        self.assertTrue(prop.qualifier.data_type.is_object())
        #
        objdescr = prop.qualifier.data_type.data_type
        self.assertTrue (hasattr(objdescr, 'array_prop'))
        self.assertEquals(DATA_TYPE_ARRAY, objdescr.array_prop.type)
        self.assertTrue( isinstance(objdescr.array_prop.qualifier, ArrayQualifier) )
        self.assertEquals(DATA_TYPE_STRING, objdescr.array_prop.qualifier.data_type)
    
    def test_complex_object(self) :
        class _Tmp(object):
            class _SubTmp(object) :
                sub_byte_property = binary_property(DATA_TYPE_BYTE)
                __binary_struct__ = (sub_byte_property,)
            byte_property = binary_property(DATA_TYPE_BYTE)
            obj_property = object_binary_property(_SubTmp)
            a1_property = array_binary_property(ArrayQualifier( DATA_TYPE_BYTE ))
            a2_property = array_binary_property(ArrayQualifier( _SubTmp ))
            a3_property = array_binary_property(ArrayQualifier( ArrayQualifier(DATA_TYPE_BYTE) ))
            a4_property = array_binary_property(ArrayQualifier( ArrayQualifier(_SubTmp) ))
            __binary_struct__ = (byte_property, obj_property, a1_property, a2_property, a3_property, a4_property)
        # initialize class properties
        t = _Tmp()
        t.byte_property = 125
        t.obj_property = _Tmp._SubTmp()
        t.obj_property.sub_byte_property = 100
        t.a1_property = (1, 2, 3)
        t.a2_property = (_Tmp._SubTmp(), _Tmp._SubTmp())
        t.a2_property[0].sub_byte_property = 50
        t.a2_property[1].sub_byte_property = 60
        t.a3_property = (ArrayContainer(DATA_TYPE_BYTE, [1, 2]), ArrayContainer(DATA_TYPE_BYTE, [3, 4]))
        t.a4_property = (ArrayContainer(_Tmp._SubTmp, [_Tmp._SubTmp()]),)
        t.a4_property[0][0].sub_byte_property = 70
        bin = BinaryFormatter.serialize(t)
        self.assertEquals(bytearray([125, 100, 0x03, 0x00, 0x01, 0x02, 0x03, 0x02, 0x00, 50, 60, 0x02, 0x00, 0x02, 0x00, 1, 2, 0x02, 0x00, 3, 4, 0x01, 0x00, 0x01, 0x00, 70]), bin)


class BinaryConstructableTest(unittest.TestCase):
    class _ElementType(object) :
        sub_property1 = binary_property(DATA_TYPE_BOOL)
        __binary_struct__ = (sub_property1, )
    
    def setUp(self):
        params = (Parameter(DATA_TYPE_WORD, 'property1'),
                  Parameter(DATA_TYPE_BYTE, 'property2'),
                  Parameter(DATA_TYPE_ARRAY, 'property3', ArrayQualifier(DATA_TYPE_BYTE)),
                  Parameter(DATA_TYPE_OBJECT, 'property4', BinaryConstructableTest._ElementType))
        self.cmd = Command(intent = 100, name = 'CommandName', parameters = params)
    
    def test_descriptor(self):
        cls = self.cmd.descriptor()
        
        self.assertTrue(issubclass(cls, ToDictionary))
        
        self.assertTrue(hasattr(cls, 'property1'))
        self.assertTrue(isinstance(cls.property1, binary_property))
        
        self.assertTrue(hasattr(cls, 'property2'))
        self.assertTrue(isinstance(cls.property2, binary_property))
        
        self.assertTrue(hasattr(cls, 'property3'))
        self.assertTrue(isinstance(cls.property3, array_binary_property))
        self.assertTrue(isinstance(cls.property3.qualifier, ArrayQualifier))
        self.assertEquals(DATA_TYPE_BYTE, cls.property3.qualifier.data_type)
        
        self.assertTrue(hasattr(cls, 'property4'))
        self.assertTrue(isinstance(cls.property4, object_binary_property))
        self.assertEquals(BinaryConstructableTest._ElementType, cls.property4.qualifier)
        self.assertTrue(hasattr(cls.property4.qualifier, 'sub_property1'))
    
    def test_top_level_scalar(self):
        pass


class ToDictionaryTest(unittest.TestCase):
    def setUp(self) :
        class _Test(ToDictionary) :
            class _SubTyp(ToDictionary) :
                i8_prop = binary_property(DATA_TYPE_SBYTE)
                __binary_struct__ = (i8_prop,)
            u8_prop  = binary_property(DATA_TYPE_BYTE)
            obj_prop = object_binary_property(_SubTyp)
            ab_prop  = array_binary_property( ArrayQualifier(DATA_TYPE_WORD) )
            ao_prop  = array_binary_property( ArrayQualifier(_SubTyp) )
            aa_prop  = array_binary_property( ArrayQualifier(ArrayQualifier(DATA_TYPE_BYTE)) )
            __binary_struct__ = (u8_prop, obj_prop, ab_prop, ao_prop, aa_prop)
        #
        self.obj = _Test()
        self.obj = _Test()
        self.obj.u8_prop = 125
        self.obj.obj_prop = _Test._SubTyp()
        self.obj.obj_prop.i8_prop = 100
        self.obj.ab_prop = (1, 2, 3, 4)
        #
        self.obj.ao_prop = (_Test._SubTyp(), _Test._SubTyp())
        self.obj.ao_prop[0].i8_prop = 1
        self.obj.ao_prop[1].i8_prop = 2
        #
        element_data_type = _Test.aa_prop.qualifier.data_type
        self.obj.aa_prop = (ArrayContainer(element_data_type, [1, 2]), ArrayContainer(element_data_type, [3, 4]))
    
    def test_basic_property(self) :
        res = self.obj.to_dict()
        self.assertTrue('u8_prop' in res)
        self.assertEquals(125, res['u8_prop'])
    
    def test_object_property(self):
        res = self.obj.to_dict()
        self.assertTrue('obj_prop' in res)
        self.assertTrue(isinstance(res['obj_prop'], dict))
        self.assertTrue('i8_prop' in res['obj_prop'])
        self.assertEquals(100, res['obj_prop']['i8_prop'])
    
    def test_array_of_basics_property(self):
        res = self.obj.to_dict()
        self.assertTrue('ab_prop' in res)
        self.assertTrue(isinstance(res['ab_prop'], list))
        self.assertEquals(4, len(res['ab_prop']))
        self.assertEquals([1, 2, 3, 4], res['ab_prop'])
    
    def test_array_of_objects_property(self):
        res = self.obj.to_dict()
        self.assertTrue('ao_prop' in res)
        self.assertTrue(isinstance(res['ao_prop'], list))
        self.assertEquals(2, len(res['ao_prop']))
        self.assertTrue( all([isinstance(i, dict) for i in res['ao_prop']]) )
        self.assertEquals(1, res['ao_prop'][0]['i8_prop'])
        self.assertEquals(2, res['ao_prop'][1]['i8_prop'])
    
    def test_array_of_array_of_basics_property(self):
        res = self.obj.to_dict()
        self.assertTrue('aa_prop' in res)
        self.assertTrue(isinstance(res['aa_prop'], list))
        self.assertEquals(1, res['aa_prop'][0][0])
        self.assertEquals(2, res['aa_prop'][0][1])
        self.assertEquals(3, res['aa_prop'][1][0])
        self.assertEquals(4, res['aa_prop'][1][1])


class UpdateableTest(unittest.TestCase) :
    class _Test(Updateable) :
        class _SubTest(object) :
            sub_property = binary_property(DATA_TYPE_SBYTE)
            __binary_struct__ = (sub_property,)
        
        class _Element(object) :
            element = binary_property(DATA_TYPE_BYTE)
            __binary_struct__ = (element,)
        
        property1 = binary_property(DATA_TYPE_BYTE)
        property2 = object_binary_property(_SubTest)
        property3 = array_binary_property(ArrayQualifier(DATA_TYPE_BYTE))
        property4 = array_binary_property(ArrayQualifier(_Element))
        property5 = array_binary_property(ArrayQualifier(ArrayQualifier(DATA_TYPE_WORD)))
        __binary_struct__ = (property1, property2, property3, property4, property5)
    
    def test_update(self) :
        obj = UpdateableTest._Test()
        obj.update({'property1': 123,
                    'property2': {'sub_property': 321},
                    'property3': [1, 2, 3],
                    'property4': [ {'element':2}, {'element':1}, {'element':0}],
                    'property5': [ [1, 2, 3], [1, 3, 2], [2, 1, 3], [2, 3, 1], [3, 2, 1], [3, 1, 2] ] })
        #
        self.assertEquals(123, obj.property1)
        self.assertTrue(hasattr(obj, 'property2'))
        self.assertTrue(isinstance(obj.property2, UpdateableTest._Test._SubTest))
        self.assertEquals(321, obj.property2.sub_property)
        #
        self.assertTrue(hasattr(obj, 'property3'))
        self.assertEquals([1,2,3], obj.property3)
        #
        self.assertTrue(hasattr(obj, 'property4'))
        self.assertEquals(3, len(obj.property4))
        self.assertTrue( all([isinstance(o, UpdateableTest._Test._Element) for o in obj.property4]) )
        self.assertEquals(2, obj.property4[0].element)
        self.assertEquals(1, obj.property4[1].element)
        self.assertEquals(0, obj.property4[2].element)
        #
        self.assertTrue(hasattr(obj, 'property5'))
        self.assertEquals(6, len(obj.property5))
        self.assertTrue( all([isinstance(o, ArrayContainer) for o in obj.property5]) )
        self.assertTrue( all([o.array.qualifier.data_type == DATA_TYPE_WORD for o in obj.property5]) )
        self.assertTrue( all([3 == len(o) for o in obj.property5]) )
        self.assertEquals(1, obj.property5[0][0])
        self.assertEquals(2, obj.property5[0][1])
        self.assertEquals(3, obj.property5[0][2])
        self.assertEquals(1, obj.property5[1][0])
        self.assertEquals(3, obj.property5[1][1])
        self.assertEquals(2, obj.property5[1][2])
        self.assertEquals(2, obj.property5[2][0])
        self.assertEquals(1, obj.property5[2][1])
        self.assertEquals(3, obj.property5[2][2])
        self.assertEquals(2, obj.property5[3][0])
        self.assertEquals(3, obj.property5[3][1])
        self.assertEquals(1, obj.property5[3][2])
        self.assertEquals(3, obj.property5[4][0])
        self.assertEquals(2, obj.property5[4][1])
        self.assertEquals(1, obj.property5[4][2])
        self.assertEquals(3, obj.property5[5][0])
        self.assertEquals(1, obj.property5[5][1])
        self.assertEquals(2, obj.property5[5][2])
    
    def test_array_updateable(self):
        class _ArrayElement(Updateable):
            top_level = array_binary_property(ArrayQualifier(DATA_TYPE_BYTE))
            __binary_struct__ = (top_level,)
        obj = _ArrayElement()
        obj.update([1, 2, 3])
        self.assertEquals(1, obj.top_level[0])
        self.assertEquals(2, obj.top_level[1])
        self.assertEquals(3, obj.top_level[2])
    
    def test_scalar_updateable(self):
        class _ScalarElement(Updateable) :
            top_level = binary_property(DATA_TYPE_BYTE)
            __binary_struct__ = (top_level,)
        obj = _ScalarElement()
        obj.update(12)
        self.assertEquals(12, obj.top_level)
        obj.update(230)
        self.assertEquals(230, obj.top_level)


class BinaryFactoryTests(unittest.TestCase):
    class _GatewayMock(object):
        reg_has_been_received = False
        device_info = None
        def registration_received(self, device_info):
            self.reg_has_been_received = True
            self.device_info = device_info
    
    def setUp(self):
        self.gateway = BinaryFactoryTests._GatewayMock()
        self.device_id = uuid.uuid1()
        rp = RegistrationPayload()
        rp.device_id = self.device_id
        rp.device_key = 'test-device-key'
        rp.device_name= 'test-device-name'
        rp.device_class_name = 'test-device-class-name'
        rp.device_class_version = 'test-device-class-version'
        rp.equipment = ( Equipment('eq-1-name', 'eq-1-code', 'eq-1-typecode'), )
        rp.notifications = ( Notification(300, 'notification-1-name',  (Parameter(DATA_TYPE_WORD, 'word_param'), Parameter(DATA_TYPE_BYTE, 'byte_param'))), )
        rp.commands = (Command(301, 'command-1-name', (Parameter(DATA_TYPE_SWORD, 'sword_param'),)), )
        self.device_reg_payload = BinaryFormatter.serialize(rp)
        self.device_reg_pkt = Packet(PACKET_SIGNATURE, 1, 0, SYS_INTENT_REGISTER, self.device_reg_payload)
    
    def tearDown(self):
        del self.gateway
    
    def test_make_connection(self):
        """
        When protocol initilizes it sends registration request into device transport
        """
        binfactory = BinaryFactory( self.gateway )
        protocol = binfactory.buildProtocol(None)
        transport = StringTransport()
        protocol.makeConnection( transport )
        # makeConnection
        bindata = transport.value()
        pkt = Packet.from_binary(bindata)
        self.assertEquals(PACKET_SIGNATURE, pkt.signature)
        self.assertEquals(1, pkt.version)
        self.assertEquals(SYS_INTENT_REQUEST_REGISTRATION, pkt.intent)
        self.assertEquals(0, len(pkt.data))
    
    def test_registration(self):
        # dataReceived registration from device
        binfactory = BinaryFactory(self.gateway)
        protocol = binfactory.buildProtocol(None)
        protocol.dataReceived(self.device_reg_pkt.to_binary())
        self.assertTrue(self.gateway.reg_has_been_received)
        self.assertNotEquals(None, self.gateway.device_info)
        self.assertEquals(str(self.device_id), self.gateway.device_info.id)
        self.assertEquals('test-device-key', self.gateway.device_info.key)
        self.assertEquals('test-device-name', self.gateway.device_info.name)
        self.assertEquals('test-device-class-name', self.gateway.device_info.device_class.name)
        self.assertEquals('test-device-class-version', self.gateway.device_info.device_class.version)
        self.assertEquals(1, len(self.gateway.device_info.equipment))
        eq = self.gateway.device_info.equipment[0]
        self.assertEquals('eq-1-name', eq.name)
        self.assertEquals('eq-1-code', eq.code)
        self.assertEquals('eq-1-typecode', eq.type)
        # test notification_descriptors
        self.assertEquals(1, len(binfactory.notification_descriptors[self.device_id]))
        self.assertTrue(300 in binfactory.notification_descriptors[self.device_id])
        notif = binfactory.notification_descriptors[self.device_id][300]
        self.assertEquals(300, notif.intent)
        self.assertNotEquals(None, notif.cls)
        self.assertTrue(hasattr(notif.cls, 'word_param'))
        self.assertTrue(hasattr(notif.cls, 'byte_param'))
        self.assertTrue(DATA_TYPE_WORD, notif.cls.word_param.type)
        self.assertTrue(DATA_TYPE_BYTE, notif.cls.byte_param.type)
        # test command_descriptors
        self.assertEquals(1, len(binfactory.command_descriptors[self.device_id]))
        self.assertTrue(301 in binfactory.command_descriptors[self.device_id])
        cmd = binfactory.command_descriptors[self.device_id][301]
        self.assertEquals(301, cmd.intent)
        self.assertNotEquals(None, cmd.cls)
        self.assertTrue(hasattr(cmd.cls, 'sword_param'))
        self.assertTrue(DATA_TYPE_SWORD, cmd.cls.sword_param.type)
    
    def test_registration2(self):
        json_str = '{"id":"e736540e-97e4-4b19-864f-103e5a4a965c","key":"key123","name":"test123",' + \
                   '"deviceClass":{"name":"dev123cls","version":"1.0"},' + \
                   '"equipment":[{"code":"tst_r","name":"test red","type":"test_red_t"},' + \
                                '{"code":"tst_g","name":"test green","type":"tst_grn_t"}],' + \
                   '"notifications":[{"intent":256,"name":"eq1","params":{"eprop":"str","state":"bool"}},' + \
                                    '{"intent":257,"name":"eq2","params":"str"},' + \
                                    '{"intent":258,"name":"eq3","params":["str"]}],' + \
                   '"commands":[{"intent":266,"name":"cmd1","params":{"e1":"str","state":"bool"}},' + \
                               '{"intent":267,"name":"SetTempResolution","params":"str"},' + \
                               '{"intent":268,"name":"SetTempInterval","params":["str"]},' + \
                               '{"intent":269,"name":"vcc"},' + \
                               '{"intent":270,"name":"SetTempInterval","params":{"equipment":"str","interval":"u16"}}' + \
                               ']}'
        obj = BinaryFormatter.deserialize_register2(json_str)
        self.assertEquals(5, len(obj.commands))
        self.assertTrue(all([isinstance(x, Command) for x in obj.commands]))
        # object top level value
        cmd0 = obj.commands[0]
        self.assertTrue(isinstance(cmd0, BinaryConstructable))
        descr0 = cmd0.descriptor()
        self.assertTrue(hasattr(descr0, 'e1'))
        self.assertTrue(isinstance(getattr(descr0, 'e1'), AbstractBinaryProperty))
        self.assertTrue(hasattr(descr0, 'state'))
        self.assertTrue(isinstance(getattr(descr0, 'state'), AbstractBinaryProperty))
        # scalar top level value
        cmd1 = obj.commands[1]
        self.assertTrue(isinstance(cmd1, BinaryConstructable))
        descr1 = cmd1.descriptor()
        self.assertTrue(hasattr(descr1, 'top_level'))
        self.assertTrue(isinstance(getattr(descr1, 'top_level'), AbstractBinaryProperty))
        self.assertEquals(DATA_TYPE_STRING, getattr(descr1, 'top_level').type)
        # array top level value
        cmd2 = obj.commands[2]
        descr2 = cmd2.descriptor()
        self.assertTrue(hasattr(descr2, 'top_level'))
        self.assertTrue(isinstance(getattr(descr2, 'top_level'), array_binary_property))
        self.assertEquals(DATA_TYPE_STRING, getattr(descr2, 'top_level').qualifier.data_type)
        # empty parameters
        cmd3 = obj.commands[3]
        descr3 = cmd3.descriptor()
        self.assertFalse(hasattr(descr3, 'top_level'))
        self.assertTrue(hasattr(descr3, '__binary_struct__'))
        self.assertEquals(0, len(descr3.__binary_struct__))
        # update tests
        o0 = descr0()
        o0.update({'e1': 'test0', 'state': True})
        self.assertEquals('test0', o0.e1)
        self.assertEquals(True, o0.state)
        # descr1
        o1 = descr1()
        o1.update('test1')
        self.assertEquals('test1', o1.top_level)
        # descr2
        o2 = descr2()
        o2.update(['test2.1', 'test2.2', 'test2.3'])
        self.assertEquals(3, len(o2.top_level))
        self.assertEquals('test2.1', o2.top_level[0])
        self.assertEquals('test2.2', o2.top_level[1])
        self.assertEquals('test2.3', o2.top_level[2])
        o2.update(('test2.1.1', 'test2.1.2'))
        self.assertEquals(2, len(o2.top_level))
        self.assertEquals('test2.1.1', o2.top_level[0])
        self.assertEquals('test2.1.2', o2.top_level[1])
        # fail tests o2
        o2.update({'test3': 'test3', 'test4': 4})
        self.assertEquals(['test2.1.1', 'test2.1.2'], o2.top_level, 'Invalid update parameter should not updates values.')
        # descr3
        o3 = descr3()
        o3.update(None)
        # fail tests o3
        o3.update([1,2,3])
        o3.update({'test1': 'test1', 'test2': 2})
        # cmd 4, creates descriptor, an object and then a command.
        cmd4 = obj.commands[4]
        descr4 = cmd4.descriptor()
        o4 = descr4()
        o4.update({'equipment':'LED_Y', 'interval':10})
        msg = Packet(PACKET_SIGNATURE, 1, 0, cmd4.intent, struct.pack('<I', 123) + BinaryFormatter.serialize_object(o4))
        bin_pkt = msg.to_binary()


class BinaryFormatterErrorTests(unittest.TestCase):
    def test_base_class(self):
        self.assertNotEquals(None, BinaryFormatterError("description")) 
        self.assertNotEquals(None, BinarySerializationError("description"))
        self.assertNotEquals(None, BinaryDeserializationError("description"))


class AbstractBinaryPropertyTests(unittest.TestCase):
    def test_auto_getter_setter(self):
        class _Test(object):
            prop1 = binary_property(DATA_TYPE_DWORD)
            prop2 = binary_property(DATA_TYPE_QWORD)
        t = _Test()
        self.assertTrue(hasattr(_Test, 'prop1'))
        self.assertTrue(hasattr(_Test, 'prop2'))
        t.prop1 = 12
        t.prop2 = 13
        self.assertEquals(12, t.prop1)
        self.assertEquals(13, t.prop2)


if __name__ == '__main__':
    unittest.main()


