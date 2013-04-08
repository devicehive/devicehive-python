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
    
    dev_id = 'e50d6085-2aba-48e9-b1c3-73c673e414be'
    
    def connected(self):
        def on_ok(result):
            print 'The application authenticated.'
            def on_subscribed(msg):
                print 'The application has subscribed to notifications. Sending test command to the device.'
                def cmd_ret(o):
                    print 'Result from command {0}'.format(o)
                self.factory.command(self.dev_id, devicehive.client.ws.WsCommand('test')).addBoth(cmd_ret)
                def on_ping(pingid):
                    print 'ping OK {0}'.format(pingid)
                def on_err(reason):
                    print 'ping failure. reason: {0}.'.format(reason)
                self.factory.ping().addCallbacks(on_ping, on_err)
            def on_subscribed_failed(rsn):
                print 'The application failed to subscribe to notifications'
            self.factory.subscribe([self.dev_id]).addCallbacks(on_subscribed, on_subscribed_failed)
        def on_fail(reason):
            print 'The application FAILED authentication.'
        self.factory.authenticate('vusr', 'password').addCallbacks(on_ok, on_fail)
    
    def do_notification(self, device_id, notification):
        print 'Notification {0} has been received for device {1}.'.format(notification, device_id)


def main():
    log.startLogging(sys.stdout)
    transport = devicehive.client.ws.WebSocketFactory(TestApp())
    transport.connect('http://pg.devicehive.com:8010')
    #transport.connect('ws://localhost:3919')
    reactor.run()


if __name__ == '__main__' :
    main()

