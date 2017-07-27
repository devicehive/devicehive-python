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
    RESPONSE_SUBSCRIPTION_ID_KEY = 'subscriptionId'

    def __init__(self, data_format_class, data_format_options, handler_class,
                 handler_options):
        Transport.__init__(self, 'http', HttpTransportError, data_format_class,
                           data_format_options, handler_class, handler_options)
        self._url = None
        self._options = None
        self._events_queue = []
        self._subscription_ids = []
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
        self._subscription_ids = []
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

    def _subscription_requests(self, action, subscription_requests):
        subscription_id = self._uuid()
        self._subscription_ids.append(subscription_id)
        subscription_thread_num = 0
        for action, request, params in subscription_requests:
            subscription_thread_name = '%s-transport-subscription-%s-%s'
            subscription_thread_name %= (self._name, subscription_id,
                                         subscription_thread_num)
            subscription_thread_num += 1
            subscription_thread = threading.Thread(target=self._subscription,
                                                   args=(subscription_id,
                                                         action, request,
                                                         params))
            subscription_thread.daemon = True
            subscription_thread.name = subscription_thread_name
            subscription_thread.start()
        return {self.REQUEST_ID_KEY: self._uuid(),
                self.REQUEST_ACTION_KEY: action,
                self.RESPONSE_STATUS_KEY: self.RESPONSE_SUCCESS_STATUS,
                self.RESPONSE_SUBSCRIPTION_ID_KEY: subscription_id}

    def _subscription(self, subscription_id, action, request, params):
        response_error_handler = params.pop('response_error_handler', None)
        response_error_handler_args = params.pop('response_error_handler_args',
                                                 None)
        response_key = params['response_key']
        params_timestamp_key = params.pop('params_timestamp_key', 'timestamp')
        response_timestamp_key = params.pop('response_timestamp_key',
                                            'timestamp')
        while self._connected and subscription_id in self._subscription_ids:
            try:
                response = self._request(action, request.copy(), **params)
                if subscription_id not in self._subscription_ids:
                    return
                response_status = response[self.RESPONSE_STATUS_KEY]
                if response_status != self.RESPONSE_SUCCESS_STATUS:
                    response_code = response[self.RESPONSE_CODE_KEY]
                    error = 'Subscription request error. Action: %s. Code: %s.'
                    error %= (action, response_code)
                    if not response_error_handler:
                        raise self._error(error)
                    if not response_error_handler(params, response_code,
                                                  *response_error_handler_args):
                        raise self._error(error)
                    response = self._request(action, request.copy(), **params)
                    if subscription_id not in self._subscription_ids:
                        return
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
                           self.RESPONSE_SUBSCRIPTION_ID_KEY: subscription_id}
                          for event in events]
                self._events_queue.append(events)
            except BaseException:
                self._exception_info = sys.exc_info()

    def _remove_subscription_requests(self, action, request):
        subscription_id = request[self.RESPONSE_SUBSCRIPTION_ID_KEY]
        if subscription_id in self._subscription_ids:
            self._subscription_ids.remove(subscription_id)
        return {self.REQUEST_ID_KEY: self._uuid(),
                self.REQUEST_ACTION_KEY: action,
                self.RESPONSE_STATUS_KEY: self.RESPONSE_SUCCESS_STATUS}

    def send_request(self, action, request, **params):
        self._ensure_connected()
        subscription_requests = params.pop('subscription_requests', [])
        if subscription_requests:
            response = self._subscription_requests(action,
                                                   subscription_requests)
            self._events_queue.append([response])
            return response[self.REQUEST_ID_KEY]
        if params.pop('remove_subscription_requests', False):
            response = self._remove_subscription_requests(action, request)
            self._events_queue.append([response])
            return response[self.REQUEST_ID_KEY]
        response = self._request(action, request, **params)
        self._events_queue.append([response])
        return response[self.REQUEST_ID_KEY]

    def request(self, action, request, **params):
        self._ensure_connected()
        subscription_requests = params.pop('subscription_requests', [])
        if subscription_requests:
            return self._subscription_requests(action, subscription_requests)
        if params.pop('remove_subscription_requests', False):
            return self._remove_subscription_requests(action, request)
        return self._request(action, request, **params)


class HttpTransportError(TransportError):
    """Http transport error."""
