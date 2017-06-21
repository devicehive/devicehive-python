from devicehive.transports.base_transport import BaseTransport
import websocket
import threading
import time
import uuid


class WebsocketTransport(BaseTransport):
    """Websocket transport class."""

    def __init__(self, data_format_class, data_format_options, handler_class,
                 handler_options, **options):
        BaseTransport.__init__(self, 'websocket', data_format_class,
                               data_format_options, handler_class,
                               handler_options)
        self._obj_id_field_name = options.get('obj_id_field_name', 'requestId')
        self._obj_action_field_name = options.get('obj_action_field_name',
                                                  'action')
        self._connect_thread = None
        self._websocket = websocket.WebSocket()
        self._pong_received = False
        self._obj_queue = []
        self._data_opcode = self._get_data_opcode()

    def _connect(self, url, options):
        ping_interval = options.get('ping_interval', None)
        timeout = options.get('timeout', None)
        self._websocket.connect(url, **options)
        self._websocket.settimeout(timeout)
        self._connected = True
        self._call_handler_method('handle_connected')
        send_ping_thread = None
        if ping_interval:
            self._pong_received = True
            send_ping_thread = threading.Thread(target=self._send_ping,
                                                args=(ping_interval,))
            send_ping_thread.daemon = True
            send_ping_thread.start()
        self._receive_data()
        self._close()
        if ping_interval:
            send_ping_thread.join()

    def _send_ping(self, ping_interval):
        while self._connected:
            if not self._pong_received:
                self._connected = False
                break
            self._websocket.ping()
            self._pong_received = False
            time.sleep(ping_interval)

    def _receive_data(self):
        while self._connected:
            if len(self._obj_queue):
                obj = self._obj_queue.pop(0)
                self._call_handler_method('handle_event', obj)
                continue
            try:
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
            except websocket.WebSocketConnectionClosedException:
                return

    def _close(self):
        self._pong_received = False
        self._obj_queue = []
        self._websocket.close()
        self._call_handler_method('handle_closed')

    def _get_data_opcode(self):
        if self._data_type() == 'text':
            return websocket.ABNF.OPCODE_TEXT
        return websocket.ABNF.OPCODE_BINARY

    def connect(self, url, **options):
        self._assert_not_connected()
        self._connect_thread = threading.Thread(target=self._connect,
                                                args=(url, options))
        self._connect_thread.daemon = True
        self._connect_thread.start()

    def request(self, action, obj, **params):
        self._assert_connected()
        obj_id = str(uuid.uuid1())
        obj[self._obj_id_field_name] = obj_id
        obj[self._obj_action_field_name] = action
        self._websocket.send(self._encode_obj(obj), opcode=self._data_opcode)
        send_time = time.time()
        timeout = params.get('timeout', 30)
        while time.time() - timeout < send_time:
            obj = self._decode_data(self._websocket.recv())
            if obj.get(self._obj_id_field_name) == obj_id:
                return obj
            self._obj_queue.append(obj)
        raise websocket.WebSocketException('Object receive timeout occurred')

    def close(self):
        self._assert_connected()
        self._connected = False

    def join(self, timeout=None):
        self._connect_thread.join(timeout)
