from devicehive.transports.transport import Transport
from devicehive.transports.transport import TransportError
import websocket
import socket
import threading
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
        self._pong_received = False
        self._event_queue = []
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
        pong_timeout = options.pop('pong_timeout', None)
        self._websocket.timeout = timeout
        self._websocket_call(self._websocket.connect, url, **options)
        self._connected = True
        self._handle_connect()
        if not pong_timeout:
            return
        ping_thread = threading.Thread(target=self._ping, args=(pong_timeout,))
        ping_thread.name = '%s-transport-ping' % self._name
        ping_thread.daemon = True
        ping_thread.start()

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
        while self._connected:
            if self._event_queue:
                event = self._event_queue.pop(0)
                self._handle_event(event)
                continue
            opcode, data = self._websocket_call(self._websocket.recv_data, True)
            if opcode == websocket.ABNF.OPCODE_TEXT:
                event = self._decode(data.decode('utf-8'))
                self._handle_event(event)
                continue
            if opcode == websocket.ABNF.OPCODE_BINARY:
                event = self._decode(data)
                self._handle_event(event)
                continue
            if opcode == websocket.ABNF.OPCODE_PONG:
                self._pong_received = True
                continue
            if opcode == websocket.ABNF.OPCODE_CLOSE:
                return

    def _disconnect(self):
        self._websocket_call(self._websocket.close)
        self._pong_received = False
        self._event_queue = []
        self._handle_disconnect()

    def _send_request(self, request_id, action, request):
        request[self.REQUEST_ID_KEY] = request_id
        request[self.REQUEST_ACTION_KEY] = action
        self._websocket_call(self._websocket.send, self._encode(request),
                             opcode=self._data_opcode)

    def _receive_response(self, request_id, timeout):
        start_time = time.time()
        while time.time() - timeout < start_time:
            response = self._decode(self._websocket_call(self._websocket.recv))
            if response.get(self.REQUEST_ID_KEY) == request_id:
                return response
            self._event_queue.append(response)
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
