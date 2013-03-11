# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

import unittest
import sys
from os import path


orig_name = __name__
orig_path = list(sys.path)
sys.path.insert(0, path.abspath(path.join(path.dirname(__file__), '..')))
try :
    utils = __import__('devicehive')
    __import__('devicehive.utils')
    utils = utils.utils
finally :
    sys.path[:] = orig_path
    __name__ = orig_name


class TestParseUrl(unittest.TestCase):
    def test_normal_parse_url(self):
        url, host, port = utils.parse_url('http://example.com/api/')
        self.assertEquals('http://example.com/api/', url)
        self.assertEquals('example.com', host)
        self.assertEquals(80, port)
    
    def test_no_lead_parse_url(self):
        url, host, port = utils.parse_url('http://example.com/api')
        self.assertEquals('http://example.com/api/', url)
        self.assertEquals('example.com', host)
        self.assertEquals(80, port)
    
    def test_def_port_parse_url(self):
        url, host, port = utils.parse_url('http://example.com:8181/api')
        self.assertEquals('http://example.com:8181/api/', url)
        self.assertEquals('example.com', host)
        self.assertEquals(8181, port)
    
    def test_default_ssl_port_parse_url(self):
        url, host, port = utils.parse_url('https://example.com/api')
        self.assertEquals('https://example.com/api/', url)
        self.assertEquals('example.com', host)
        self.assertEquals(443, port)
    
    def test_redef_ssl_port_parse_url(self):
        url, host, port = utils.parse_url('https://example.com:9191/api/')
        self.assertEquals('https://example.com:9191/api/', url)
        self.assertEquals('example.com', host)
        self.assertEquals(9191, port)


if __name__ == '__main__' :
    unittest.main()

