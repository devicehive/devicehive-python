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
import requests
import threading
import sys
import time


class HttpTransport(Transport):
    """Http transport class."""

    def __init__(self, data_format_class, data_format_options, handler_class,
                 handler_options):
        super(HttpTransport, self).__init__('http', HttpTransportError,
                                            data_format_class,
                                            data_format_options, handler_class,
                                            handler_options)
        self._url = None
        self._options = None
        self._events_queue_sleep = None
        self._events_queue = []
        self._subscription_ids = []
        self._success_codes = [200, 201, 204]

    def _connect(self, url, **options):
        self._url = url
        self._options = options
        self._events_queue_sleep_time = options.pop('events_queue_sleep_time',
                                                    1e-6)
        if not self._url.endswith('/'):
            self._url += '/'
        self._connected = True
        self._handle_connect()

    def _receive(self):
        while self._connected and not self._exception_info:
            if not self._events_queue:
                time.sleep(self._events_queue_sleep_time)
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

    def _request(self, request_id, action, request, **params):
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
        response = {self.REQUEST_ID_KEY: request_id,
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

    def _subscription_request(self, request_id, action, subscription_request,
                              response_subscription_id_key):
        subscription_id = subscription_request['subscription_id']
        self._subscription_ids.append(subscription_id)
        subscription_thread_name = '%s-transport-subscription-%s'
        subscription_thread_name %= (self._name, subscription_id)
        subscription_thread = threading.Thread(target=self._subscription,
                                               kwargs=subscription_request)
        subscription_thread.daemon = True
        subscription_thread.name = subscription_thread_name
        subscription_thread.start()
        return {self.REQUEST_ID_KEY: request_id,
                self.REQUEST_ACTION_KEY: action,
                self.RESPONSE_STATUS_KEY: self.RESPONSE_SUCCESS_STATUS,
                response_subscription_id_key: subscription_id}

    def _subscription(self, subscription_id, request_id, action, request,
                      params):
        response_error_handler = params.pop('response_error_handler', None)
        response_error_handler_args = params.pop('response_error_handler_args',
                                                 None)
        response_key = params['response_key']
        params_timestamp_key = params.pop('params_timestamp_key', 'timestamp')
        response_timestamp_key = params.pop('response_timestamp_key',
                                            'timestamp')
        response_subscription_id_key = params.pop(
            'response_subscription_id_key', 'subscriptionId')
        while subscription_id in self._subscription_ids:
            try:
                response = self._request(request_id, action, request.copy(),
                                         **params)
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
                    response = self._request(request_id, action, request.copy(),
                                             **params)
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
                           response_subscription_id_key: subscription_id}
                          for event in events]
                self._events_queue.append(events)
            except:
                self._exception_info = sys.exc_info()

    def _remove_subscription_request(self, request_id, action, subscription_id,
                                     response_code, response_error):
        if subscription_id not in self._subscription_ids:
            return {self.REQUEST_ID_KEY: request_id,
                    self.REQUEST_ACTION_KEY: action,
                    self.RESPONSE_STATUS_KEY: self.RESPONSE_ERROR_STATUS,
                    self.RESPONSE_CODE_KEY: response_code,
                    self.RESPONSE_ERROR_KEY: response_error}
        self._subscription_ids.remove(subscription_id)
        return {self.REQUEST_ID_KEY: request_id,
                self.REQUEST_ACTION_KEY: action,
                self.RESPONSE_STATUS_KEY: self.RESPONSE_SUCCESS_STATUS}

    def send_request(self, request_id, action, request, **params):
        self._ensure_connected()
        subscription_request = params.pop('subscription_request', {})
        response_subscription_id_key = params.pop(
            'response_subscription_id_key', 'subscriptionId')
        remove_subscription_request = params.pop('remove_subscription_request',
                                                 {})
        if subscription_request:
            response = self._subscription_request(request_id, action,
                                                  subscription_request,
                                                  response_subscription_id_key)
        elif remove_subscription_request:
            response = self._remove_subscription_request(
                request_id, action, **remove_subscription_request)
        else:
            response = self._request(request_id, action, request, **params)
        self._events_queue.append([response])

    def request(self, request_id, action, request, **params):
        self._ensure_connected()
        subscription_request = params.pop('subscription_request', {})
        response_subscription_id_key = params.pop(
            'response_subscription_id_key', 'subscriptionId')
        remove_subscription_request = params.pop('remove_subscription_request',
                                                 {})
        if subscription_request:
            return self._subscription_request(request_id, action,
                                              subscription_request,
                                              response_subscription_id_key)
        if remove_subscription_request:
            return self._remove_subscription_request(
                request_id, action, **remove_subscription_request)
        return self._request(request_id, action, request, **params)


class HttpTransportError(TransportError):
    """Http transport error."""
