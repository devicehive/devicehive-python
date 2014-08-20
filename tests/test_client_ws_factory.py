# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

from unittest import TestCase

from zope.interface import implements

import devicehive.interfaces

from devicehive.client.ws import WebSocketFactory


class TestApp(object):
    implements(devicehive.interfaces.IClientApp)

    def do_notification(self, device_id, notification):
        pass

    def connected(self):
        pass


class ClientWsFactoryClientUrl(TestCase):
    def setUp(self):
        self.factory = WebSocketFactory(TestApp())

    def test_undefined_url(self):
        self.factory.url = None
        self.assertEquals('/client', self.factory.get_client_url())

    def test_root_url(self):
        self.factory.url = 'ws://localhost'
        self.assertEquals('/client', self.factory.get_client_url())

    def test_root_url_ends_with_slash(self):
        self.factory.url = 'ws://localhost/'
        self.assertEquals('/client', self.factory.get_client_url())

    def test_non_root_url(self):
        self.factory.url = 'ws://localhost/test/websocket'
        self.assertEquals('/test/websocket/client', self.factory.get_client_url())

    def test_non_root_ends_with_slash_url(self):
        self.factory.url = 'ws://localhost/test/websocket/'
        self.assertEquals('/test/websocket/client', self.factory.get_client_url())

