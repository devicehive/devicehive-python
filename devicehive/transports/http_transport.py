from devicehive.transports.transport import Transport
from devicehive.transports.transport import TransportRequestException
import requests
import threading
import queue


class HttpTransport(Transport):
    """Http transport class."""

    RESPONSE_SUCCESS_STATUS = 'success'
    RESPONSE_ERROR_STATUS = 'error'
    RESPONSE_STATUS_KEY = 'status'
    RESPONSE_CODE_KEY = 'code'
    RESPONSE_ERROR_KEY = 'error'

    def __init__(self, data_format_class, data_format_options, handler_class,
                 handler_options):
        Transport.__init__(self, 'http', data_format_class, data_format_options,
                           handler_class, handler_options)
        self._connection_thread = None
        self._base_url = None
        self._events_queue = queue.Queue()
        self._poll_threads = {}
        self._success_codes = [200, 201, 204]
        self.request_poll_id_key = 'subscriptionId'

    def _connection(self, url):
        self._base_url = url
        if not self._base_url.endswith('/'):
            self._base_url += '/'
        self._connect()
        self._receive()
        self._close()

    def _connect(self):
        self._connected = True
        self._call_handler_method('handle_connect')

    def _receive(self):
        while self._connected:
            for poll_thread in self._poll_threads.values():
                if not poll_thread.is_alive():
                    return
            if self._events_queue.empty():
                continue
            for event in self._events_queue.get():
                self._call_handler_method('handle_event', event)
                if not self._connected:
                    return

    def _close(self):
        self._events_queue = queue.Queue()
        self._poll_threads = {}
        self._call_handler_method('handle_close')

    def _http_request(self, method, url, **params):
        response = requests.request(method, url, **params)
        code = response.status_code
        data = response.text if self._data_type == 'text' else response.content
        return code, data

    def _request(self, action, request, **params):
        method = params.pop('method', 'GET')
        url = self._base_url + params.pop('url')
        request_delete_keys = params.pop('request_delete_keys', [])
        request_key = params.pop('request_key', None)
        response_key = params.pop('response_key', None)
        for request_delete_key in request_delete_keys:
            del request[request_delete_key]
        if request:
            if request_key:
                request = request[request_key]
            params['data'] = self._encode(request)
        code, data = self._http_request(method, url, **params)
        response = {self.REQUEST_ID_KEY: self._uuid(),
                    self.REQUEST_ACTION_KEY: action}
        if code in self._success_codes:
            response[self.RESPONSE_STATUS_KEY] = self.RESPONSE_SUCCESS_STATUS
            if not data:
                return response
            response_data = self._decode(data)
            if response_key:
                response[response_key] = response_data
                return response
            for key in response_data:
                response[key] = response_data[key]
            return response
        response[self.RESPONSE_STATUS_KEY] = self.RESPONSE_ERROR_STATUS
        response[self.RESPONSE_CODE_KEY] = code
        if not data:
            return response
        response_data = self._decode(data)
        response[self.RESPONSE_ERROR_KEY] = response_data.get('message')
        return response

    def _poll_request(self, action, request, **params):
        poll_id = self._uuid()
        self._poll_threads[poll_id] = threading.Thread(target=self._poll,
                                                       args=(action, poll_id,
                                                             request, params))
        self._poll_threads[poll_id].daemon = True
        self._poll_threads[poll_id].name = 'http-transport-poll-%s' % poll_id
        self._poll_threads[poll_id].start()
        return {self.REQUEST_ID_KEY: self._uuid(),
                self.REQUEST_ACTION_KEY: action,
                self.RESPONSE_STATUS_KEY: self.RESPONSE_SUCCESS_STATUS,
                self.request_poll_id_key: poll_id}

    def _poll(self, action, poll_id, request, params):
        data_key = params['data_key']
        poll_action = params.pop('poll_action')
        params_timestamp_key = params.pop('params_timestamp_key', 'timestamp')
        event_timestamp_key = params.pop('event_timestamp_key', 'timestamp')
        while self._connected and self._poll_threads.get(poll_id, None):
            response = self._request(action, request, **params)
            if response[self.RESPONSE_STATUS_KEY] != \
                    self.RESPONSE_SUCCESS_STATUS:
                return
            events = response[data_key]
            if not len(events):
                continue
            timestamp = events[-1][event_timestamp_key]
            if not params.get('params'):
                params['params'] = {}
            params['params'][params_timestamp_key] = timestamp
            events = [{self.REQUEST_ACTION_KEY: poll_action,
                       self.request_poll_id_key: poll_id,
                       data_key: event} for event in events]
            self._events_queue.put(events)

    def _stop_poll_request(self, action, request):
        poll_id = request[self.request_poll_id_key]
        if poll_id not in self._poll_threads:
            raise HttpTransportRequestException('Polling does not exist')
        poll_thread = self._poll_threads[poll_id]
        del self._poll_threads[poll_id]
        poll_thread.join()
        return {self.REQUEST_ID_KEY: self._uuid(),
                self.REQUEST_ACTION_KEY: action,
                self.RESPONSE_STATUS_KEY: self.RESPONSE_SUCCESS_STATUS}

    def connect(self, url, **options):
        self._ensure_not_connected()
        self._connection_thread = threading.Thread(target=self._connection,
                                                   args=(url,))
        self._connection_thread.daemon = True
        self._connection_thread.name = 'http-transport-connection'
        self._connection_thread.start()

    def send_request(self, action, request, **params):
        self._ensure_connected()
        poll = params.pop('poll', None)
        if poll is None:
            response = self._request(action, request, **params)
            self._events_queue.put([response])
            return response[self.REQUEST_ID_KEY]
        if poll:
            response = self._poll_request(action, request, **params)
            self._events_queue.put([response])
            return response[self.REQUEST_ID_KEY]
        response = self._stop_poll_request(action, request)
        self._events_queue.put([response])
        return response[self.REQUEST_ID_KEY]

    def request(self, action, request, **params):
        self._ensure_connected()
        poll = params.pop('poll', None)
        if poll is None:
            return self._request(action, request, **params)
        if poll:
            return self._poll_request(action, request, **params)
        return self._stop_poll_request(action, request)

    def close(self):
        self._ensure_connected()
        self._connected = False

    def join(self, timeout=None):
        self._connection_thread.join(timeout)


class HttpTransportRequestException(TransportRequestException):
    """Http transport request exception."""
    pass
