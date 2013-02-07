# -*- encoding: utf8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8 encoding=utf-8

from datetime import datetime
from urlparse import urlsplit, urljoin


__all__ = ['parse_url', 'parse_date']


def parse_url(device_hive_url) :
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


def parse_date(date_str) :
    if len(date_str) > 19:
        return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%f')
    else :
        return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')


