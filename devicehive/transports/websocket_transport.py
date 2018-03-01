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


from devicehive.transports.transport import Transport
from devicehive.transports.transport import TransportError
import websocket
import socket
import threading
import sys
import time


class WebsocketTransport(Transport):
    """Websocket transport class."""

    def __init__(self, data_format_class, data_format_options, handler_class,
                 handler_options):
        super(WebsocketTransport, self).__init__('websocket',
                                                 WebsocketTransportError,
                                                 data_format_class,
                                                 data_format_options,
                                                 handler_class, handler_options)
        self._websocket = websocket.WebSocket()
        self._connection_lock = threading.Lock()
        self._event_queue_sleep_time = None
        self._response_sleep_time = None
        self._pong_received = False
        self._event_queue = []
        self._responses = {}
        if self._text_data_type:
            self._data_opcode = websocket.ABNF.OPCODE_TEXT
        else:
            self._data_opcode = websocket.ABNF.OPCODE_BINARY

    def _websocket_call(self, websocket_method, *args, **kwargs):
        try:
            return websocket_method(*args, **kwargs)
        except (websocket.WebSocketException, socket.error) as websocket_error:
            error = websocket_error
        raise self._error(error)

    def _connect(self, url, **options):
        timeout = options.pop('timeout', None)
        event_queue_sleep_time = options.pop('event_queue_sleep_time', 1e-6)
        response_sleep_time = options.pop('response_sleep_time', 1e-6)
        pong_timeout = options.pop('pong_timeout', None)
        self._websocket.timeout = timeout
        self._event_queue_sleep_time = event_queue_sleep_time
        self._response_sleep_time = response_sleep_time
        self._websocket_call(self._websocket.connect, url, **options)
        self._connected = True
        event_thread = threading.Thread(target=self._event)
        event_thread.name = '%s-transport-event' % self._name
        event_thread.daemon = True
        event_thread.start()
        if pong_timeout:
            ping_thread = threading.Thread(target=self._ping,
                                           args=(pong_timeout,))
            ping_thread.name = '%s-transport-ping' % self._name
            ping_thread.daemon = True
            ping_thread.start()
        self._handle_connect()

    def _event(self):
        while self._connected:
            try:
                with self._connection_lock:
                    opcode, data = self._websocket_call(
                        self._websocket.recv_data, True)
                if opcode in (websocket.ABNF.OPCODE_TEXT,
                              websocket.ABNF.OPCODE_BINARY):
                    if opcode == websocket.ABNF.OPCODE_TEXT:
                        data = data.decode('utf-8')
                    event = self._decode(data)
                    request_id = event.get(self.REQUEST_ID_KEY)
                    if not request_id:
                        self._event_queue.append(event)
                        continue
                    self._responses[request_id] = event
                    continue
                if opcode == websocket.ABNF.OPCODE_PONG:
                    self._pong_received = True
                    continue
                if opcode == websocket.ABNF.OPCODE_CLOSE:
                    return
            except:
                self._exception_info = sys.exc_info()

    def _ping(self, pong_timeout):
        while self._connected:
            try:
                self._websocket_call(self._websocket.ping)
            except self._error:
                self._connected = False
                return
            self._pong_received = False
            time.sleep(pong_timeout)
            if not self._pong_received:
                self._connected = False
                return

    def _receive(self):
        while self._connected and not self._exception_info:
            if not self._event_queue:
                time.sleep(self._event_queue_sleep_time)
                continue
            for event in self._event_queue:
                self._handle_event(event)
                if not self._connected:
                    return
            self._event_queue = []

    def _disconnect(self):
        self._websocket_call(self._websocket.ping)
        with self._connection_lock:
            self._websocket_call(self._websocket.close)
        self._pong_received = False
        self._event_queue = []
        self._responses = {}
        self._handle_disconnect()

    def _send_request(self, request_id, action, request):
        request[self.REQUEST_ID_KEY] = request_id
        request[self.REQUEST_ACTION_KEY] = action
        self._websocket_call(self._websocket.send, self._encode(request),
                             opcode=self._data_opcode)

    def _receive_response(self, request_id, timeout):
        start_time = time.time()
        while time.time() - timeout < start_time:
            response = self._responses.get(request_id)
            if response:
                del self._responses[request_id]
                return response
            time.sleep(self._response_sleep_time)
        raise self._error('Response timeout.')

    def send_request(self, request_id, action, request, **params):
        self._ensure_connected()
        self._send_request(request_id, action, request)

    def request(self, request_id, action, request, **params):
        self._ensure_connected()
        timeout = params.pop('timeout', 30)
        self._send_request(request_id, action, request)
        return self._receive_response(request_id, timeout)


class WebsocketTransportError(TransportError):
    """Websocket transport error."""
