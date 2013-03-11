#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

"""
This example shows API of DeviceHive client library.
"""

import sys
import os

from twisted.python import log
from twisted.internet import reactor
from zope.interface import implements

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import devicehive
import devicehive.client.ws
import devicehive.interfaces


class TestApp(object):
    
    implements(devicehive.interfaces.IClientApp)
    
    def connected(self):
        def on_ok(result):
            print 'The application authenticated.'
            def on_subscribed(msg):
                print 'The application has subscribed to notifications'
                # def on_unsbcr(msg):
                #    print 'Unsubscribed'
                #def on_fail_unsubcr(resn):
                #    print 'Failed to unsubscribe'
                #self.factory.unsubscribe(['b125698d-61bd-40d7-b65e-e1f86852a166']).addCallbacks(on_unsbcr, on_fail_unsubcr)
            def on_subscribed_failed(rsn):
                print 'The application failed to subscribe to notifications'
            self.factory.subscribe(['b125698d-61bd-40d7-b65e-e1f86852a166', 'e50d6085-2aba-48e9-b1c3-73c673e414be']).addCallbacks(on_subscribed, on_subscribed_failed)
        def on_fail(reason):
            print 'The application FAILED authentication.'
        self.factory.authenticate('vusr', 'password').addCallbacks(on_ok, on_fail)


def main():
    log.startLogging(sys.stdout)
    transport = devicehive.client.ws.WebSocketFactory(TestApp())
    transport.connect('ws://ecloud.dataart.com:8010')
    reactor.run()


if __name__ == '__main__' :
    main()

