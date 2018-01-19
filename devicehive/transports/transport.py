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


import sys
import threading


class Transport(object):
    """Transport class."""

    REQUEST_ID_KEY = 'requestId'
    REQUEST_ACTION_KEY = 'action'
    RESPONSE_SUCCESS_STATUS = 'success'
    RESPONSE_ERROR_STATUS = 'error'
    RESPONSE_STATUS_KEY = 'status'
    RESPONSE_CODE_KEY = 'code'
    RESPONSE_ERROR_KEY = 'error'

    def __init__(self, name, error, data_format_class, data_format_options,
                 handler_class, handler_options):
        self._name = name
        self._error = error
        self._data_format = data_format_class(**data_format_options)
        self._handler = handler_class(self, **handler_options)
        self._connection_thread = None
        self._connected = False
        self._exception_info = None

    @property
    def _text_data_type(self):
        return self._data_format.text_data_type

    @property
    def _binary_data_type(self):
        return self._data_format.binary_data_type

    def _encode(self, obj):
        return self._data_format.encode(obj)

    def _decode(self, data):
        return self._data_format.decode(data)

    def _handle_connect(self):
        self._handler.handle_connect()

    def _handle_event(self, event):
        self._handler.handle_event(event)

    def _handle_disconnect(self):
        self._handler.handle_disconnect()

    def _ensure_not_connected(self):
        if not self._connected:
            return
        raise self._error('Connection has already created.')

    def _ensure_connected(self):
        if self._connected:
            return
        raise self._error('Connection has not created.')

    def _connection(self, url, options):
        try:
            self._connect(url, **options)
            self._receive()
            self._disconnect()
        except:
            self._exception_info = sys.exc_info()

    def _connect(self, url, **options):
        raise NotImplementedError

    def _receive(self):
        raise NotImplementedError

    def _disconnect(self):
        raise NotImplementedError

    @property
    def name(self):
        return self._name

    @property
    def error(self):
        return self._error

    @property
    def handler(self):
        return self._handler

    @property
    def connected(self):
        return self._connected

    @property
    def exception_info(self):
        return self._exception_info

    def connect(self, url, **options):
        self._ensure_not_connected()
        self._connection_thread = threading.Thread(target=self._connection,
                                                   args=(url, options))
        self._connection_thread.name = '%s-transport-connection' % self._name
        self._connection_thread.daemon = True
        self._connection_thread.start()

    def disconnect(self):
        self._ensure_connected()
        self._connected = False

    def join(self, timeout=None):
        self._connection_thread.join(timeout)

    def is_alive(self):
        return self._connection_thread.is_alive()

    def send_request(self, request_id, action, request, **params):
        raise NotImplementedError

    def request(self, request_id, action, request, **params):
        raise NotImplementedError


class TransportError(IOError):
    """Transport error."""
