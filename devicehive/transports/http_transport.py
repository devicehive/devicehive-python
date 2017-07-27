from devicehive.transports.transport import Transport
from devicehive.transports.transport import TransportError
import requests
import threading
import sys


class HttpTransport(Transport):
    """Http transport class."""

    RESPONSE_SUCCESS_STATUS = 'success'
    RESPONSE_ERROR_STATUS = 'error'
    RESPONSE_STATUS_KEY = 'status'
    RESPONSE_CODE_KEY = 'code'
    RESPONSE_ERROR_KEY = 'error'
    RESPONSE_SUBSCRIBE_ID_KEY = 'subscriptionId'

    def __init__(self, data_format_class, data_format_options, handler_class,
                 handler_options):
        Transport.__init__(self, 'http', HttpTransportError, data_format_class,
                           data_format_options, handler_class, handler_options)
        self._url = None
        self._options = None
        self._events_queue = []
        self._subscribe_threads = {}
        self._success_codes = [200, 201, 204]

    def _connect(self, url, **options):
        self._url = url
        self._options = options
        if not self._url.endswith('/'):
            self._url += '/'
        self._connected = True
        self._handle_connect()

    def _receive(self):
        while self._connected and not self._exception_info:
            if not self._events_queue:
                continue
            for event in self._events_queue.pop(0):
                self._handle_event(event)
                if not self._connected:
                    return

    def _disconnect(self):
        self._events_queue = []
        self._subscribe_threads = {}
        self._handle_disconnect()

    def _request_call(self, method, url, **params):
        options = self._options.copy()
        options.update(params)
        try:
            response = requests.request(method, url, **options)
            code = response.status_code
            if self._text_data_type:
                return code, response.text
            return code, response.content
        except requests.RequestException as http_error:
            error = http_error
        raise self._error(error)

    def _request(self, action, request, **params):
        method = params.pop('method', 'GET')
        url = self._url + params.pop('url')
        request_delete_keys = params.pop('request_delete_keys', [])
        request_key = params.pop('request_key', None)
        response_key = params.pop('response_key', None)
        for request_delete_key in request_delete_keys:
            del request[request_delete_key]
        if request:
            if request_key:
                request = request[request_key]
            params['data'] = self._encode(request)
        code, data = self._request_call(method, url, **params)
        response = {self.REQUEST_ID_KEY: self._uuid(),
                    self.REQUEST_ACTION_KEY: action}
        if code in self._success_codes:
            response[self.RESPONSE_STATUS_KEY] = self.RESPONSE_SUCCESS_STATUS
            if not data:
                return response
            if response_key:
                response[response_key] = self._decode(data)
                return response
            response.update(self._decode(data))
            return response
        response[self.RESPONSE_STATUS_KEY] = self.RESPONSE_ERROR_STATUS
        response[self.RESPONSE_CODE_KEY] = code
        if not data:
            return response
        try:
            response_error = self._decode(data)['message']
        except Exception:
            response_error = data
        response[self.RESPONSE_ERROR_KEY] = response_error
        return response

    def _subscribe_requests(self, action, subscribe_requests):
        subscribe_id = self._uuid()
        subscribe_threads = []
        for action, request, params in subscribe_requests:
            name = '%s-transport-subscribe-%s-%s'
            subscribe_thread_name = name % (self._name, subscribe_id,
                                            len(subscribe_threads))
            subscribe_thread = threading.Thread(target=self._subscribe,
                                                args=(subscribe_id, action,
                                                      request, params))
            subscribe_thread.daemon = True
            subscribe_thread.name = subscribe_thread_name
            subscribe_thread.start()
            subscribe_threads.append(subscribe_thread)
        self._subscribe_threads[subscribe_id] = subscribe_threads
        return {self.REQUEST_ID_KEY: self._uuid(),
                self.REQUEST_ACTION_KEY: action,
                self.RESPONSE_STATUS_KEY: self.RESPONSE_SUCCESS_STATUS,
                self.RESPONSE_SUBSCRIBE_ID_KEY: subscribe_id}

    def _subscribe(self, subscribe_id, action, request, params):
        response_error_handler = params.pop('response_error_handler', None)
        response_error_handler_args = params.pop('response_error_handler_args',
                                                 None)
        response_key = params['response_key']
        params_timestamp_key = params.pop('params_timestamp_key', 'timestamp')
        response_timestamp_key = params.pop('response_timestamp_key',
                                            'timestamp')
        while self._connected and not self._exception_info:
            try:
                response = self._request(action, request.copy(), **params)
                response_status = response[self.RESPONSE_STATUS_KEY]
                if response_status != self.RESPONSE_SUCCESS_STATUS:
                    response_code = response[self.RESPONSE_CODE_KEY]
                    error = 'Subscribe request error. Action: %s. Code: %s.'
                    error = error % (action, response_code)
                    if not response_error_handler:
                        raise self._error(error)
                    if not response_error_handler(params, response_code,
                                                  *response_error_handler_args):
                        raise self._error(error)
                    response = self._request(action, request.copy(), **params)
                    response_status = response[self.RESPONSE_STATUS_KEY]
                    if response_status != self.RESPONSE_SUCCESS_STATUS:
                        raise self._error(error)
                events = response[response_key]
                if not len(events):
                    continue
                timestamp = events[-1][response_timestamp_key]
                if not params.get('params'):
                    params['params'] = {}
                params['params'][params_timestamp_key] = timestamp
                events = [{self.REQUEST_ACTION_KEY: action,
                           response_key: event,
                           self.RESPONSE_SUBSCRIBE_ID_KEY: subscribe_id}
                          for event in events]
                self._events_queue.append(events)
            except BaseException:
                self._exception_info = sys.exc_info()

    def send_request(self, action, request, **params):
        # TODO: add unsubscribe.
        self._ensure_connected()
        subscribe_requests = params.pop('subscribe_requests', [])
        if subscribe_requests:
            response = self._subscribe_requests(action, subscribe_requests)
            self._events_queue.append([response])
            return response[self.REQUEST_ID_KEY]
        response = self._request(action, request, **params)
        self._events_queue.append([response])
        return response[self.REQUEST_ID_KEY]

    def request(self, action, request, **params):
        # TODO: add unsubscribe.
        self._ensure_connected()
        subscribe_requests = params.pop('subscribe_requests', [])
        if subscribe_requests:
            return self._subscribe_requests(action, subscribe_requests)
        return self._request(action, request, **params)


class HttpTransportError(TransportError):
    """Http transport error."""
