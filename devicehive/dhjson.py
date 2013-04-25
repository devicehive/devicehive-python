# -*- coding: utf8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

"""
LR JSON parser which support unquoted property names.
"""

from collections import OrderedDict


class Parser(object) :
    offset = 0
    def __init__(self, buff):
        self.buff = buff
    
    def peek_ch(self):
        return self.buff[self.offset : self.offset + 1]
    
    def next_ch(self):
        self.offset += 1
        return self.peek_ch()
    
    def lookup(self, num):
        return self.buff[self.offset + num : self.offset + num + 1]
    
    def skip_spaces(self):
        ch = self.peek_ch()
        while ch.isspace() :
            ch = self.next_ch()
    
    def read_until(self, eset) :
        ESC = {'t': '\t', 'r': '\r', 'n': '\n', 'f': '\x0c', '\\': '\\', '/': '/', '"': '"', "'": "'"}
        ch  = self.next_ch()
        res = ''
        escape = ch == '\\'
        while (ch != '') and (escape or (ch not in eset)) :
            if escape :
                ch = self.next_ch()
                if ch is None or ch == '' or ch not in """trn"'\\f/""" :
                    raise ValueError('Malformed escape sequence. Value {0}.'.format(self.buff[self.offset:]))
                else :
                    ch = ESC[ch]
                escape = False
            res += ch
            ch = self.next_ch()
            escape = ch == '\\'
        if escape :
            raise ValueError('Malformed string.')
        return res
    
    def parse_number_str(self, addnums = ''):
        res = ''
        ch = self.peek_ch()
        while (ch is not None) and (ch.isdigit() or (len(addnums) > 0 and ch != '' and ch in addnums)) :
            res += ch
            ch = self.next_ch()
        return res
    
    def parse_number(self):
        ch = self.peek_ch()
        if ch == '0' :
            lch = self.lookup(1)
            if lch == 'x' or lch == 'X' :
                self.next_ch()
                self.next_ch()
                num = self.parse_number_str(addnums = 'abcdefABCDEF')
                return int(num, 16)
            elif lch.isdigit() :
                self.next_ch()
                num = self.parse_number_str()
                return int(num, 8)
        num = self.parse_number_str()
        return int(num, 10)
        
    def parse_identifier(self):
        res = ''
        ch = self.peek_ch()
        while ch.isalnum() or ch == '_' :
            res += ch
            ch = self.next_ch()
        return res
    
    def parse_string(self):
        res = ''
        ch = self.peek_ch()
        if ch == '"' :
            res = self.read_until('"')
        elif ch == "'" :
            res = self.read_until("'")
        self.next_ch()
        return res
    
    def parse_array(self):
        res = []
        self.next_ch()
        self.skip_spaces()
        ch = self.peek_ch()
        while ch != ']' :
            res.append(self.parse_value())
            self.skip_spaces()
            ch = self.peek_ch()
            if ch != ']' and ch != ',' :
                raise ValueError('Malformed json array {0}'.format(self.buff[self.offset:]))
            elif ch == ',' :
                self.next_ch()
                self.skip_spaces()
                ch = self.peek_ch()
        self.next_ch()
        return res
    
    def parse_object_property_name(self):
        key = ''
        ch = self.peek_ch()
        if ch == '"' or ch == "'" :
            key = self.parse_string()
        elif ch == '_' or ch.isalpha() :
            key = self.parse_identifier()
        else :
            raise ValueError('Malformed JSON object property name <<<{0}>>>.'.format(self.buff[self.offset:]))
        return key
    
    def parse_object_property(self):
        key = self.parse_object_property_name()
        self.skip_spaces()
        
        ch = self.peek_ch()
        if ch != ':' :
            raise ValueError('Malformed JSON object. Property name expected <<<{0}>>>.'.format(self.buff[self.offset:]))
        ch = self.next_ch()
        self.skip_spaces()
        
        val = self.parse_value()
        return (key, val)
    
    def parse_object(self):
        res = OrderedDict()
        self.next_ch()
        self.skip_spaces()
        ch = self.peek_ch()
        while ch != '}' :
            key, val = self.parse_object_property()
            res[key] = val
            
            self.skip_spaces()
            ch = self.peek_ch()
            if ch != '}' and ch != ',' :
                raise ValueError('Malformed json object <<<{0}>>>.'.format(self.buff[self.offset:]))
            elif ch == ',' :
                self.next_ch()
                self.skip_spaces()
                ch = self.peek_ch()
        self.next_ch()
        return res
    
    def parse_value(self):
        ch = self.peek_ch()
        if ch == '"' or ch == "'" :
            return self.parse_string()
        elif ch == '[' :
            return self.parse_array()
        elif ch == '{' :
            return self.parse_object()
        elif ch.isdigit() :
            return self.parse_number()
        elif ch.isalpha() or ch == '_' :
            return self.parse_identifier()
        else :
            raise ValueError('Failed to parse json. Malformed string {0}.'.format(self.buff[self.offset:]))
    
    def parse(self):
        self.skip_spaces()
        if len(self.buff[self.offset:]) > 0 :
            return self.parse_value()
        else :
            return None

