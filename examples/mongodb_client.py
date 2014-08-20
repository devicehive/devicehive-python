#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

import sys
import os

from time import sleep

from twisted.python import log
from twisted.internet import reactor
from zope.interface import implements
from pymongo import MongoClient

import devicehive
import devicehive.client.ws
import devicehive.interfaces


class MongoApp(object):
    
    implements(devicehive.interfaces.IClientApp)

    def __init__(self, mongo_client, device_id, user, password):
        self.mongo_client = mongo_client
        self.dev_id = device_id
        self.user = user
        self.password = password

    def do_connect(self):
        self.factory.authenticate(self.user, self.password).addCallbacks(self.on_auth_ok, self.on_auth_fail)

    def on_auth_ok(self, result):
        log.msg('The application successfully authenticated itself.')
        self.do_subscribe()

    def on_auth_fail(self, reason):
        log.err('The application failed to authenticate itself.')

    def connected(self):
        log.msg('Connecting to the devicehive server.')
        self.do_connect()

    def do_notification(self, device_id, notification):
        log.msg('Notification {0} has been received for device {1}.'.format(notification, device_id))
        db = self.mongo_client.devicehive
        db.notifications.insert(notification.to_dict())

    def on_subscribe_ok(self, msg):
        log.msg('Sucessfully subscribed to notifications. Message: {0}.'.format(msg))

    def on_subscribe_fail(self, reason):
        log.err('Failed to subscribe to notifications. Reason: {0}.'.format(reason))

    def do_subscribe(self):
        log.msg('subscribing to notifications.')
        self.factory.subscribe([self.dev_id]).addCallbacks(self.on_subscribe_ok, self.on_subscribe_fail)


def main():
    log.startLogging(sys.stdout)

    mongo_client = MongoClient(host='IP_OR_HOST_NAME', port=27017, document_class='DOC_CLASS')
    log.msg('Mongo client {}.'.format(mongo_client))

    app = MongoApp(mongo_client, '9f33566e-1f8f-11e2-8979-c42c030dd6a5', 'USER_NAME', 'PASSWORD')
    transport = devicehive.client.ws.WebSocketFactory(app)
    transport.connect('ws://IP_OR_HOST_NAME:8080/DeviceHiveJava/websocket/')
    reactor.run()
    mongo_client.disconnect()


if __name__ == '__main__' :
    main()

