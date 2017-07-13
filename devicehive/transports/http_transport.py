from devicehive.transports.transport import Transport
from devicehive.transports.transport import TransportRequestException
import sys
import threading
import requests


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
        Transport.__init__(self, 'http', data_format_class, data_format_options,
                           handler_class, handler_options)
        self._base_url = None
        self._events_queue = []
        self._subscribe_threads = {}
        self._success_codes = [200, 201, 204]

    def _connection(self, url, options):
        self._base_url = url
        if not self._base_url.endswith('/'):
            self._base_url += '/'
        try:
            self._connect()
            self._receive()
            self._close()
        except BaseException:
            self._exception_info = sys.exc_info()

    def _connect(self):
        self._connected = True
        self._call_handler_method('handle_connect')

    def _receive(self):
        while self._connected:
            for subscribe_thread in self._subscribe_threads.values():
                if not subscribe_thread.is_alive():
                    return
            if not self._events_queue:
                continue
            for event in self._events_queue.pop(0):
                self._call_handler_method('handle_event', event)
                if not self._connected:
                    return

    def _close(self):
        self._events_queue = []
        self._subscribe_threads = {}
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

    def _subscribe_request(self, action, request, **params):
        subscribe_id = self._uuid()
        subscribe_thread = threading.Thread(target=self._subscribe,
                                            args=(subscribe_id, action, request,
                                                  params))
        subscribe_thread_name = '%s-transport-subscribe-%s' % (self._name,
                                                               subscribe_id)
        self._subscribe_threads[subscribe_id] = subscribe_thread
        self._subscribe_threads[subscribe_id].daemon = True
        self._subscribe_threads[subscribe_id].name = subscribe_thread_name
        self._subscribe_threads[subscribe_id].start()
        return {self.REQUEST_ID_KEY: self._uuid(),
                self.REQUEST_ACTION_KEY: action,
                self.RESPONSE_STATUS_KEY: self.RESPONSE_SUCCESS_STATUS,
                self.RESPONSE_SUBSCRIBE_ID_KEY: subscribe_id}

    def _subscribe(self, subscribe_id, action, request, params):
        response_key = params['response_key']
        params_timestamp_key = params.pop('params_timestamp_key', 'timestamp')
        response_timestamp_key = params.pop('response_timestamp_key',
                                            'timestamp')
        response_success_status = self.RESPONSE_SUCCESS_STATUS
        while self._connected and self._subscribe_threads.get(subscribe_id):
            response = self._request(action, request.copy(), **params)
            if response[self.RESPONSE_STATUS_KEY] != response_success_status:
                # TODO: handle error status here.
                return
            events = response[response_key]
            if not len(events):
                continue
            timestamp = events[-1][response_timestamp_key]
            if not params.get('params'):
                params['params'] = {}
            params['params'][params_timestamp_key] = timestamp
            # TODO: add action to event.
            events = [{response_key: event,
                       self.RESPONSE_SUBSCRIBE_ID_KEY: subscribe_id}
                      for event in events]
            self._events_queue.append(events)

    def _unsubscribe_request(self, action, request):
        subscribe_id = request[self.RESPONSE_SUBSCRIBE_ID_KEY]
        if subscribe_id not in self._subscribe_threads:
            raise HttpTransportRequestException('Subscription does not exist')
        subscribe_thread = self._subscribe_threads[subscribe_id]
        del self._subscribe_threads[subscribe_id]
        subscribe_thread.join()
        return {self.REQUEST_ID_KEY: self._uuid(),
                self.REQUEST_ACTION_KEY: action,
                self.RESPONSE_STATUS_KEY: self.RESPONSE_SUCCESS_STATUS}

    def send_request(self, action, request, **params):
        self._ensure_connected()
        subscribe = params.pop('subscribe', False)
        unsubscribe = params.pop('unsubscribe', False)
        if subscribe:
            response = self._subscribe_request(action, request, **params)
            self._events_queue.append([response])
            return response[self.REQUEST_ID_KEY]
        if unsubscribe:
            response = self._unsubscribe_request(action, request)
            self._events_queue.append([response])
            return response[self.REQUEST_ID_KEY]
        response = self._request(action, request, **params)
        self._events_queue.append([response])
        return response[self.REQUEST_ID_KEY]

    def request(self, action, request, **params):
        self._ensure_connected()
        subscribe = params.pop('subscribe', False)
        unsubscribe = params.pop('unsubscribe', False)
        if subscribe:
            return self._subscribe_request(action, request, **params)
        if unsubscribe:
            return self._unsubscribe_request(action, request)
        return self._request(action, request, **params)


class HttpTransportRequestException(TransportRequestException):
    """Http transport request exception."""
    pass
