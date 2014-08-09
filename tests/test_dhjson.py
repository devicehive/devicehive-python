# -*- coding: utf8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

import unittest

from devicehive.dhjson import Parser


class DhJsonTestCase1(unittest.TestCase):
    def test_string(self):
        p = Parser("'hello all'")
        self.assertEquals('hello all', p.parse())
    
    def test_string_dq_and_space(self):
        p = Parser(' "hello all" ')
        self.assertEquals('hello all', p.parse())
    
    def test_parse_number_10(self):
        p = Parser('123')
        self.assertEquals(123, p.parse())
    
    def test_parse_number_16(self):
        p = Parser('0x123')
        self.assertEquals(0x123, p.parse())
    
    def test_parse_number_8(self):
        p = Parser('012')
        self.assertEquals(10, p.parse())
    
    def test_parse_number_8(self):
        p = Parser('0')
        self.assertEquals(0, p.parse())
    
    def test_parse_identifier_1(self):
        p = Parser('test123_321')
        self.assertEquals('test123_321', p.parse())

    def test_parse_identifier_2(self):
        p = Parser('__test123_321')
        self.assertEquals('__test123_321', p.parse())
    
    def test_parse_identifier_2(self):
        p = Parser('__test123_321')
        self.assertEquals('__test123_321', p.parse())
    
    def test_simple_array_1(self):
        p = Parser('[1,2,3]')
        self.assertEquals([1, 2, 3, ], p.parse())
    
    def test_simple_array_2(self):
        p = Parser('[1 , 2 , 3,4 , 5,6 ]')
        self.assertEquals([1, 2, 3, 4, 5, 6, ], p.parse())
    
    def test_empty_array_1(self):
        p = Parser('[]')
        self.assertEquals([], p.parse())

    def test_empty_array_1(self):
        p = Parser('[ ]')
        self.assertEquals([], p.parse())
    
    def test_mixed_array(self):
        p = Parser('["test", 1, hello]')
        self.assertEquals(['test', 1, 'hello'], p.parse())
    
    def test_simple_object_1(self):
        p = Parser('{"hello":1}')
        self.assertEquals({'hello':1}, p.parse())

    def test_simple_object_2(self):
        p = Parser("""{"hello":1, '123': 0x123 ,_test: "test"}""")
        self.assertEquals({'hello':1, '123': 0x123, '_test': 'test'}, p.parse())
    
    def test_simple_complex_1(self):
        p = Parser("""{"arr": [ 1, 2 , 3], 'obj': { prop : 1 }}""")
        self.assertEquals({'arr':[1,2,3], 'obj': {'prop': 1}}, p.parse())
    
    def test_order_test(self):
        p = Parser("""{"b1": 1, 'a2': 2, 'c3': 3 }""")
        r = [i for i in p.parse()]
        self.assertEquals('b1', r[0])
        self.assertEquals('a2', r[1])
        self.assertEquals('c3', r[2])
    

class EmptyTestCase(unittest.TestCase):
    def test_empty_1(self):
        p = Parser('')
        self.assertIsNone(p.parse())
    
    def test_empty_2(self):
        p = Parser('   ')
        self.assertIsNone(p.parse())
    
    def test_empty_3(self):
        p = Parser('\t \n')
        self.assertIsNone(p.parse())


class EscapeSequenceTestCase(unittest.TestCase):
    def test_esc_1(self):
        p = Parser(r'"\\"')
        self.assertEquals('\\', p.parse())

    def test_esc_2(self):
        p = Parser(r'"\""')
        self.assertEquals('"', p.parse())
    
    def test_esc_3(self):
        p = Parser(r'"\\""')
        self.assertEquals('\\', p.parse())


class DhJsonTestCase2(unittest.TestCase):
    def test_complex(self):
        p = Parser(""" { id:'03684ca0-6dee-46d2-98b7-06f2cd079f5c',
                key:'5b2e34b4-995a-4d66-8b0f-392232bc1563',
                name:'Arduino Pins',
                deviceClass:{
                    name:'Arduino',
                    version:'1.0'},
                    equipment:[],
                    commands:[
                    {intent:1001,name:'getPinMode',params:[u8]},
                    {intent:1002,name:'setPinMode',params:{pin:u8,mode:u8}},
                    {intent:1003,name:'pinRead',params:[u8]},
                    {intent:1004,name:'pinWrite',params:{pin:u8,value:u16}}
                    ],
                notifications:[
                    {intent:2001,name:'pinMode',params:{pin:u8,mode:u8}},
                    {intent:2003,name:'pinRead',params:{pin:u8,value:u16}}
                ]
            }""")
        self.assertIsNotNone(p.parse())


if __name__ == '__main__':
    unittest.main()

