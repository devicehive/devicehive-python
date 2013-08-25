# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

import json
from datetime import datetime
from urlparse import urlsplit, urljoin
from twisted.internet.protocol import Protocol
from twisted.internet.defer import Deferred, succeed, fail
from twisted.web.iweb import IBodyProducer
from zope.interface import implements


__all__ = ['parse_url', 'parse_date', 'url_path', 'TextDataConsumer', 'EmptyDataProducer']


def parse_url(device_hive_url):
    if not device_hive_url.endswith('/'):
        device_hive_url += '/'
    url = urlsplit(device_hive_url)
    netloc_split = url.netloc.split(':')
    port = 80
    host = netloc_split[0]
    if url.scheme == 'https':
        port = 443
    if len(netloc_split) == 2:
        port = int(netloc_split[1], 10)
    return (device_hive_url, host, port)


def url_path(base_uri, api_uri):
    uri = urlsplit(urljoin(base_uri, api_uri))
    path = uri.path
    if len(uri.query) > 0 :
        path += '?' + uri.query
    return path


def parse_date(date_str) :
    """
    Converts a date-time string into a datetime object.
    """
    if len(date_str) > 19:
        return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%f')
    else :
        return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')


class TextDataConsumer(Protocol):
    """
    Converts a text input into a C{str}.
    """
    
    def __init__(self, deferred):
        self.deferred = deferred
        self.text = ''
    
    def dataReceived(self, data):
        self.text += data
    
    def connectionLost(self, reason):
        self.deferred.callback(self.text)


class JsonDataConsumer(Protocol):
    """
    JsonDataConsumer receives JSON data as an input and
    then converts it into C{dict} type.
    """
    
    def __init__(self, deferred):
        self.deferred = deferred
        self.data = []
    
    def dataReceived(self, data):
        self.data.append(data)
    
    def connectionLost(self, reason):
        data = json.loads(''.join(self.data))
        self.deferred.callback(data)


class EmptyDataProducer(object):
    
    implements(IBodyProducer)
    
    def __init__(self):
        self.length = 0
    
    def startProducing(self, consumer):
        try:
            consumer.write('')
            return succeed(None)
        except Exception, error:
            return fail(error)
    
    def stopProducing(self):
        pass
