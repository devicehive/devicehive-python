# Copyright (C) 2018 DataArt
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================


from devicehive.data_formats.json_data_format import JsonDataFormat
from devicehive.api_handler import ApiHandler
import time
import six


class DeviceHive(object):
    """Device hive class."""

    def __init__(self, handler_class, *handler_args, **handler_kwargs):
        self._api_handler_options = {'handler_class': handler_class,
                                     'handler_args': handler_args,
                                     'handler_kwargs': handler_kwargs}
        self._transport_name = None
        self._transport = None

    def _init_transport(self):
        name = 'devicehive.transports.%s_transport' % self._transport_name
        class_name = '%sTransport' % self._transport_name.title()
        transport_module = __import__(name, globals(), locals(), [name])
        transport_class = getattr(transport_module, class_name)
        self._transport = transport_class(JsonDataFormat, {}, ApiHandler,
                                          self._api_handler_options)

    def _ensure_transport_disconnect(self):
        if self._transport.connected:
            self._transport.disconnect()

    @staticmethod
    def transport_name(transport_url):
        if transport_url[0:4] == 'http':
            return 'http'
        if transport_url[0:2] == 'ws':
            return 'websocket'

    @property
    def transport(self):
        return self._transport

    @property
    def handler(self):
        return self._transport.handler.handler

    def connect(self, transport_url, **options):
        self._transport_name = self.transport_name(transport_url)
        assert self._transport_name, 'Unexpected transport url scheme'
        transport_keep_alive = options.pop('transport_keep_alive', True)
        transport_alive_sleep_time = options.pop('transport_alive_sleep_time',
                                                 1e-6)
        connect_timeout = options.pop('connect_timeout', 30)
        max_num_connect = options.pop('max_num_connect', 10)
        connect_interval = options.pop('connect_interval', 1)
        auth = {'login': options.pop('login', None),
                'password': options.pop('password', None),
                'refresh_token': options.pop('refresh_token', None),
                'access_token': options.pop('access_token', None)}
        api_init = options.pop('api_init', True)
        self._api_handler_options['auth'] = auth
        self._api_handler_options['api_init'] = api_init
        self._init_transport()
        if not transport_keep_alive:
            self._ensure_transport_disconnect()
            self._transport.connect(transport_url, **options)
            return
        connect_time = time.time()
        num_connect = 0
        while True:
            self._ensure_transport_disconnect()
            self._transport.connect(transport_url, **options)
            while self._transport.is_alive():
                time.sleep(transport_alive_sleep_time)
            exception_info = self._transport.exception_info
            if exception_info and not isinstance(exception_info[1],
                                                 self._transport.error):
                six.reraise(*exception_info)
            if not self.handler.api.connected:
                return
            if time.time() - connect_time < connect_timeout:
                num_connect += 1
                if num_connect > max_num_connect:
                    six.reraise(*exception_info)
                time.sleep(connect_interval)
                continue
            connect_time = time.time()
            num_connect = 0
