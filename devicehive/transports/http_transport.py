from devicehive.transports.base_transport import BaseTransport
from devicehive.transports.base_transport import BaseTransportException
import requests
import threading
import queue


class HttpTransport(BaseTransport):
    """Http transport class."""

    def __init__(self, data_format_class, data_format_options, handler_class,
                 handler_options):
        BaseTransport.__init__(self, data_format_class,
                               data_format_options, handler_class,
                               handler_options, 'http')
        self._connection_thread = None
        self._base_url = None
        self._events_queue = queue.Queue()
        self._poll_threads = {}
        self._success_codes = [200, 201, 204]
        self.request_poll_id_key = 'subscriptionId'
        self.success_status = 'success'
        self.error_status = 'error'
        self.response_status_key = 'status'
        self.response_code_key = 'code'
        self.response_error_key = 'error'

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
        self._call_handler_method('handle_closed')

    def _request(self, action, request, **params):
        method = params.pop('method', 'GET')
        url = self._base_url + params.pop('url')
        merge_data = params.pop('merge_data', False)
        data_key = params.pop('data_key', None)
        if request:
            params['data'] = self._encode(request)
        resp = requests.request(method, url, **params)
        resp_data = resp.text if self._data_type == 'text' else resp.content
        response = {self.request_id_key: self._uuid(),
                    self.request_action_key: action}
        if resp.status_code in self._success_codes:
            response[self.response_status_key] = self.success_status
            if merge_data:
                resp_data = self._decode(resp_data)
                for field in resp_data:
                    response[field] = resp_data[field]
                return response
            if data_key:
                response[data_key] = self._decode(resp_data)
            return response
        response[self.response_status_key] = self.error_status
        response[self.response_code_key] = resp.status_code
        response[self.response_error_key] = self._decode(resp_data)['message']
        return response

    def _poll_request(self, action, request, **params):
        poll_id = self._uuid()
        self._poll_threads[poll_id] = threading.Thread(target=self._poll,
                                                       args=(action, poll_id,
                                                             request, params))
        self._poll_threads[poll_id].daemon = True
        self._poll_threads[poll_id].name = 'http-transport-poll-%s' % poll_id
        self._poll_threads[poll_id].start()
        return {self.request_id_key: self._uuid(),
                self.request_action_key: action,
                self.response_status_key: self.success_status,
                self.request_poll_id_key: poll_id}

    def _poll(self, action, poll_id, request, params):
        data_key = params['data_key']
        poll_action = params.pop('poll_action')
        params_timestamp_key = params.pop('params_timestamp_key', 'timestamp')
        event_timestamp_key = params.pop('event_timestamp_key', 'timestamp')
        while self._connected and self._poll_threads.get(poll_id, None):
            response = self._request(action, request, **params)
            if response[self.response_status_key] != self.success_status:
                return
            events = response[data_key]
            if not len(events):
                continue
            timestamp = events[-1][event_timestamp_key]
            if not params.get('params'):
                params['params'] = {}
            params['params'][params_timestamp_key] = timestamp
            events = [{self.request_action_key: poll_action,
                       self.request_poll_id_key: poll_id,
                       data_key: event} for event in events]
            self._events_queue.put(events)

    def _stop_poll_request(self, action, request):
        poll_id = request[self.request_poll_id_key]
        if poll_id not in self._poll_threads:
            raise HttpTransportException('Polling does not exist')
        poll_thread = self._poll_threads[poll_id]
        del self._poll_threads[poll_id]
        poll_thread.join()
        return {self.request_id_key: self._uuid(),
                self.request_action_key: action,
                self.response_status_key: self.success_status}

    def connect(self, url, **options):
        self._assert_not_connected()
        self._connection_thread = threading.Thread(target=self._connection,
                                                   args=(url,))
        self._connection_thread.daemon = True
        self._connection_thread.name = 'http-transport-connection'
        self._connection_thread.start()

    def send_request(self, action, request, **params):
        self._assert_connected()
        poll = params.pop('poll', None)
        if poll is None:
            response = self._request(action, request, **params)
            self._events_queue.put([response])
            return response[self.request_id_key]
        if poll:
            response = self._poll_request(action, request, **params)
            self._events_queue.put([response])
            return response[self.request_id_key]
        response = self._stop_poll_request(action, request)
        self._events_queue.put([response])
        return response[self.request_id_key]

    def request(self, action, request, **params):
        self._assert_connected()
        poll = params.pop('poll', None)
        if poll is None:
            return self._request(action, request, **params)
        if poll:
            return self._poll_request(action, request, **params)
        return self._stop_poll_request(action, request)

    def close(self):
        self._assert_connected()
        self._connected = False

    def join(self, timeout=None):
        self._connection_thread.join(timeout)


class HttpTransportException(BaseTransportException):
    """Http transport exception."""
    pass
