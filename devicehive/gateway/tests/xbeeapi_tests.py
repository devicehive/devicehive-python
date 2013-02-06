# -*- encoding: utf8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8 encoding=utf-8

import sys
from os import path
import unittest


orig_name = __name__
orig_path = list(sys.path)
sys.path.insert(0, path.abspath(path.join(path.dirname(__file__), '..')))
try :
    xbee_module = __import__('xbeeapi')
    globals().update(vars(xbee_module))
finally :
    sys.path[:] = orig_path
    __name__ = orig_name


class EscapeUnescapeTests(unittest.TestCase):
    def test_escape_normal(self):
        esc_data = escape_data( [1, 0x7e, 2] )
        self.assertEquals(bytearray([1, 0x7d, 0x5e, 2]), esc_data)
    
    def test_unescape_normal(self):
        unesc_data = unescape_data(bytearray([1, 0x7d, 0x5e, 2]))
        self.assertEquals([1, 0x7e, 2], unesc_data)

if __name__ == '__main__':
    unittest.main()

