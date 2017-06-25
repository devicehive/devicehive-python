from devicehive.transports.base_transport import BaseTransport
import websocket
import threading
import time
import uuid


class WebsocketTransport(BaseTransport):
    """Websocket transport class."""

    def __init__(self, data_format_class, data_format_options, handler_class,
                 handler_options):
        BaseTransport.__init__(self, 'websocket', data_format_class,
                               data_format_options, handler_class,
                               handler_options)
        self._connect_thread = None
        self._websocket = websocket.WebSocket()
        self._pong_received = False
        self._obj_queue = []
        self._data_opcode = self._get_data_opcode()

    def _connect(self, url, options):
        timeout = options.get('timeout', None)
        pong_timeout = options.get('pong_timeout', None)
        self._websocket.connect(url, **options)
        self._websocket.settimeout(timeout)
        self._connected = True
        self._call_handler_method('handle_connected')
        if pong_timeout:
            send_ping_thread = threading.Thread(target=self._send_ping,
                                                args=(pong_timeout,))
            send_ping_thread.daemon = True
            send_ping_thread.start()
        self._receive_data()
        self._close()

    def _send_ping(self, pong_timeout):
        while self._connected:
            self._websocket.ping()
            self._pong_received = False
            time.sleep(pong_timeout)
            if not self._pong_received:
                self._connected = False
                return

    def _receive_data(self):
        while self._connected:
            if len(self._obj_queue):
                obj = self._obj_queue.pop(0)
                self._call_handler_method('handle_event', obj)
                continue
            opcode, frame = self._websocket.recv_data_frame(True)
            if opcode == websocket.ABNF.OPCODE_TEXT:
                obj = self._decode_data(frame.data.decode('utf-8'))
                self._call_handler_method('handle_event', obj)
                continue
            if opcode == websocket.ABNF.OPCODE_BINARY:
                obj = self._decode_data(frame.data)
                self._call_handler_method('handle_event', obj)
                continue
            if opcode == websocket.ABNF.OPCODE_PONG:
                self._pong_received = True
                continue
            if opcode == websocket.ABNF.OPCODE_CLOSE:
                return

    def _close(self):
        self._pong_received = False
        self._obj_queue = []
        self._websocket.close()
        self._call_handler_method('handle_closed')

    def _get_data_opcode(self):
        if self._data_type == 'text':
            return websocket.ABNF.OPCODE_TEXT
        return websocket.ABNF.OPCODE_BINARY

    def connect(self, url, **options):
        self._assert_not_connected()
        self._connect_thread = threading.Thread(target=self._connect,
                                                args=(url, options))
        self._connect_thread.daemon = True
        self._connect_thread.start()

    def send_request(self, obj, **params):
        self._assert_connected()
        obj_id = str(uuid.uuid1())
        obj['requestId'] = obj_id
        obj['action'] = params['action']
        self._websocket.send(self._encode_obj(obj), opcode=self._data_opcode)
        return obj_id

    def request(self, obj, **params):
        timeout = params.get('timeout', 30)
        obj_id = self.send_request(obj, **params)
        send_time = time.time()
        while time.time() - timeout < send_time:
            obj = self._decode_data(self._websocket.recv())
            if obj.get('requestId') == obj_id:
                return obj
            self._obj_queue.append(obj)
        raise WebsocketTransportException('Object receive timeout occurred')

    def close(self):
        self._assert_connected()
        self._connected = False

    def join(self, timeout=None):
        self._connect_thread.join(timeout)


class WebsocketTransportException(websocket.WebSocketException):
    """Websocket transport exception."""
    pass
