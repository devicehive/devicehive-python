from mock import patch, Mock
from unittest import TestCase

from devicehive import connectDeviceHive, reactor


class ConnectDeviceHiveTestCase(TestCase):
    def setUp(self):
        self.factory = Mock()

    def test_calls_http(self):
        with patch('twisted.internet.reactor.connectTCP') as f:
            connectDeviceHive('http://example.com', self.factory)
        self.assertTrue(f.called)

    def test_calls_https(self):
        with patch.object(reactor, 'connectTCP') as f:
            connectDeviceHive('https://example.com', self.factory)
        self.assertTrue(f.called)
