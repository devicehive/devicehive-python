# -*- encoding: utf8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8 encoding=utf-8

import unittest
import sys
from array import array
from os import path
from zope.interface import implements
from twisted.test.proto_helpers import MemoryReactor, StringTransport, AccumulatingProtocol


orig_name = __name__
orig_path = list(sys.path)
sys.path.insert(0, path.abspath(path.join(path.dirname(__file__), '..', '..')))
try :
    devicehive = __import__('devicehive')
finally :
    sys.path[:] = orig_path
    __name__ = orig_name


class WebSocketProtocol13Test(unittest.TestCase):
    def test_send_frame(self):
        trans = StringTransport()
        proto = devicehive.WebSocketProtocol13(None)
        proto.makeConnection(trans)
        proto.send_frame(True, 2, b'1234')
        data = trans.value()
        self.assertEquals(0x82, ord(data[0:1]))
        self.assertEquals(0x84, ord(data[1:2]))
        # test payload
        mask = data[2:6]
        pload = data[6:]
        unmasked = array('B', [ ord(pload[i]) ^ ord(mask[i % 4]) for i in range(len(pload))]).tostring()
        self.assertEquals(b'1234', unmasked)


if __name__ == '__main__' :
    unittest.main()

