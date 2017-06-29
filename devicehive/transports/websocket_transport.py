from devicehive.transports.base_transport import BaseTransport
from devicehive.transports.base_transport import BaseTransportException
import websocket
import threading
import time


class WebsocketTransport(BaseTransport):
    """Websocket transport class."""

    def __init__(self, data_format_class, data_format_options, handler_class,
                 handler_options):
        BaseTransport.__init__(self, data_format_class, data_format_options,
                               handler_class, handler_options, 'websocket')
        self._connection_thread = None
        self._websocket = websocket.WebSocket()
        self._pong_received = False
        self._event_queue = []
        if self._data_type == 'text':
            self._data_opcode = websocket.ABNF.OPCODE_TEXT
        else:
            self._data_opcode = websocket.ABNF.OPCODE_BINARY
        self.request_action_key = 'action'

    def _connection(self, url, options):
        pong_timeout = options.pop('pong_timeout', None)
        self._connect(url, **options)
        if pong_timeout:
            ping_thread = threading.Thread(target=self._ping,
                                           args=(pong_timeout,))
            ping_thread.name = 'websocket-transport-ping'
            ping_thread.daemon = True
            ping_thread.start()
        self._receive()
        self._close()

    def _connect(self, url, **options):
        timeout = options.pop('timeout', None)
        self._websocket.connect(url, **options)
        self._websocket.settimeout(timeout)
        self._connected = True
        self._call_handler_method('handle_connected')

    def _ping(self, pong_timeout):
        while self._connected:
            self._websocket.ping()
            self._pong_received = False
            time.sleep(pong_timeout)
            if not self._pong_received:
                self._connected = False
                return

    def _receive(self):
        while self._connected:
            if len(self._event_queue):
                event = self._event_queue.pop(0)
                self._call_handler_method('handle_event', event)
                continue
            opcode, frame = self._websocket.recv_data_frame(True)
            if opcode == websocket.ABNF.OPCODE_TEXT:
                event = self._decode(frame.data.decode('utf-8'))
                self._call_handler_method('handle_event', event)
                continue
            if opcode == websocket.ABNF.OPCODE_BINARY:
                event = self._decode(frame.data)
                self._call_handler_method('handle_event', event)
                continue
            if opcode == websocket.ABNF.OPCODE_PONG:
                self._pong_received = True
                continue
            if opcode == websocket.ABNF.OPCODE_CLOSE:
                return

    def _close(self):
        self._websocket.close()
        self._pong_received = False
        self._event_queue = []
        self._call_handler_method('handle_closed')

    def _send_request(self, request, **params):
        request_id = self._uuid()
        request[self.request_id_key] = request_id
        request[self.request_action_key] = params.pop('action')
        self._websocket.send(self._encode(request), opcode=self._data_opcode)
        return request_id

    def connect(self, url, **options):
        self._assert_not_connected()
        self._connection_thread = threading.Thread(target=self._connection,
                                                   args=(url, options))
        self._connection_thread.name = 'websocket-transport-connection'
        self._connection_thread.daemon = True
        self._connection_thread.start()

    def send_request(self, request, **params):
        self._assert_connected()
        return self._send_request(request, **params)

    def request(self, request, **params):
        self._assert_connected()
        timeout = params.pop('timeout', 30)
        request_id = self._send_request(request, **params)
        send_time = time.time()
        while time.time() - timeout < send_time:
            response = self._decode(self._websocket.recv())
            if response.get(self.request_id_key) == request_id:
                return response
            self._event_queue.append(response)
        raise WebsocketTransportException('Response receive timeout occurred')

    def close(self):
        self._assert_connected()
        self._connected = False

    def join(self, timeout=None):
        self._connection_thread.join(timeout)


class WebsocketTransportException(BaseTransportException):
    """Websocket transport exception."""
    pass
