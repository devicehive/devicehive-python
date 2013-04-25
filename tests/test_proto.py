# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

import sys
import os
import unittest
import json
from zope.interface import implements
from twisted.internet import reactor
from twisted.web.client import HTTP11ClientProtocol
from twisted.test.proto_helpers import MemoryReactor, StringTransport, AccumulatingProtocol

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import devicehive
import devicehive.poll


class TestReactorFunc(unittest.TestCase):
	def test_has_connectDeviceHive(self):
		self.assertTrue(hasattr(reactor, 'connectDeviceHive'))


class TestRegisterRequest(unittest.TestCase):
    class FakeDevice(object):
        implements(devicehive.interfaces.IDeviceInfo)
        id = ''
        key = 'fake-device'
        name = 'fake-device'
        status = 'Online'
        data = None
        network = devicehive.Network(id = 'netid', name='netname', key='netkey', descr='net descr'),
        device_class = devicehive.DeviceClass(name='devcls-name', version='0.1'),
        equipment = [devicehive.Equipment('eq-name', 'eq-code', 'eq-type'),]
    
	class FakeFactory(object):
		def __init__(self, device_delegate):
			self.device_delegate = device_delegate
			self.uri = 'http://localhost/'
			self.host = 'localhost'
			self.info = FakeDevice()
    
	def setUp(self):
		self.device_delegate = TestRegisterRequest.FakeDeviceDelegate()
		self.factory = TestRegisterRequest.FakeFactory(self.device_delegate)
		self.transport = StringTransport()
		self.protocol = HTTP11ClientProtocol()
		self.protocol.makeConnection(self.transport)
    
	def test_request(self):
		request = devicehive.poll.RegisterRequest(self.factory)
		r = self.protocol.request(request)
		def request_done(resp):
			self.assertTrue(200, resp.code)
		r.addCallback(request_done)
		self.protocol.dataReceived('HTTP/1.1 200 OK\r\nContent-Length: 0\r\nConnection: close\r\n\r\n')
		data = json.dumps(self.device_delegate.registration_info())
		headers = '\r\n'.join(('PUT /device/device-id HTTP/1.1',
			'Connection: close',
			'Content-Length: {0}'.format(len(data)),
			'Content-Type: application/json',
			'Host: localhost',
			'Auth-Deviceid: {0}'.format(self.device_delegate.device_id()),
			'Auth-Devicekey: {0}'.format(self.device_delegate.device_key()),
			'Accept: application/json'))
		self.assertEquals(headers + '\r\n\r\n' + data, str(self.transport.value()))


if __name__ == '__main__':
	unittest.main()

