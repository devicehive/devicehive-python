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


from devicehive.api_response import ApiResponse
from devicehive.api_response import ApiResponseError
from devicehive.transports.transport import TransportError
import uuid
import logging


logger = logging.getLogger(__name__)


class ApiRequest(object):
    """Api request class."""

    def __init__(self, api):
        self._api = api
        self._action = None
        self._request = {}
        self._params = {'subscription_request': {},
                        'response_subscription_id_key': 'subscriptionId',
                        'remove_subscription_request': {},
                        'method': 'GET',
                        'url': None,
                        'request_delete_keys': [],
                        'request_key': None,
                        'params': {},
                        'headers': {},
                        'response_key': None}

    @staticmethod
    def _uuid():
        return str(uuid.uuid4())

    @property
    def http_transport(self):
        return self._api.transport.name == 'http'

    @property
    def websocket_transport(self):
        return self._api.transport.name == 'websocket'

    def action(self, action):
        self._action = action

    def set(self, key, value, request_key=False):
        if not value:
            return
        self._request[key] = value
        if not request_key:
            return
        self._params['request_key'] = key

    def subscription_request(self, subscription_api_request):
        request = subscription_api_request.extract(self._uuid(), self._uuid())
        self._params['subscription_request'] = request

    def response_subscription_id_key(self, key):
        self._params['response_subscription_id_key'] = key

    def remove_subscription_request(self, remove_subscription_api_request):
        request = remove_subscription_api_request.extract()
        self._params['remove_subscription_request'] = request

    def method(self, method):
        self._params['method'] = method

    def url(self, url, **args):
        for key in args:
            value = args[key]
            url = url.replace('{%s}' % key, str(value))
            self._request[key] = value
            self._params['request_delete_keys'].append(key)
        self._params['url'] = url

    def param(self, key, value):
        if not value:
            return
        self._request[key] = value
        self._params['request_delete_keys'].append(key)
        self._params['params'][key] = value

    def header(self, name, value):
        self._params['headers'][name] = value

    def response_key(self, key):
        self._params['response_key'] = key

    def execute(self, error_message):
        request_id = self._uuid()
        request = self._request.copy()
        logger.debug('Request id: %s. Action: %s. Request: %s. Params: %s.',
                     request_id, self._action, request, self._params)
        response = self._api.transport.request(request_id, self._action,
                                               request, **self._params)
        api_response = ApiResponse(response, self._params['response_key'])
        logger.debug('Response id: %s. Action: %s. Success: %s. Response: %s.',
                     api_response.id, api_response.action, api_response.success,
                     api_response.response)
        if api_response.success:
            return api_response.response
        raise ApiResponseError(error_message, self._api.transport.name,
                               api_response.code, api_response.error)


class AuthApiRequest(ApiRequest):
    """Auth api request class."""

    def execute(self, error_message):
        self.header(*self._api.token.auth_header)
        try:
            return super(AuthApiRequest, self).execute(error_message)
        except ApiResponseError as api_response_error:
            if api_response_error.code != 401:
                raise
        self._api.token.auth()
        self.header(*self._api.token.auth_header)
        return super(AuthApiRequest, self).execute(error_message)


class SubscriptionApiRequest(object):
    """Subscription api request class."""

    def __init__(self):
        self._action = None
        self._request = {}
        self._params = {'response_subscription_id_key': 'subscriptionId',
                        'method': 'GET',
                        'url': None,
                        'params': {},
                        'headers': {},
                        'response_key': None,
                        'params_timestamp_key': 'timestamp',
                        'response_timestamp_key': 'timestamp'}

    def action(self, action):
        self._action = action

    def set(self, key, value):
        if not value:
            return
        self._request[key] = value

    def response_subscription_id_key(self, key):
        self._params['response_subscription_id_key'] = key

    def method(self, method):
        self._params['method'] = method

    def url(self, url, **args):
        for key in args:
            value = args[key]
            url = url.replace('{%s}' % key, str(value))
        self._params['url'] = url

    def param(self, key, value):
        if not value:
            return
        self._params['params'][key] = value

    def header(self, name, value):
        self._params['headers'][name] = value

    def response_key(self, key):
        self._params['response_key'] = key

    def params_timestamp_key(self, key):
        self._params['params_timestamp_key'] = key

    def response_timestamp_key(self, key):
        self._params['response_timestamp_key'] = key

    def extract(self, subscription_id, request_id):
        return {'subscription_id': subscription_id,
                'request_id': request_id,
                'action': self._action,
                'request': self._request,
                'params': self._params}


class AuthSubscriptionApiRequest(SubscriptionApiRequest):
    """Auth subscription api request class."""

    def __init__(self, api):
        super(AuthSubscriptionApiRequest, self).__init__()
        auth_header_name, auth_header_value = api.token.auth_header
        self._params['headers'][auth_header_name] = auth_header_value
        self._params['response_error_handler'] = self.response_error_handler
        self._params['response_error_handler_args'] = [api.token]

    @staticmethod
    def response_error_handler(params, response_code, token):
        if response_code != 401:
            return
        try:
            token.auth()
            auth_header_name, auth_header_value = token.auth_header
            params['headers'][auth_header_name] = auth_header_value
            return True
        except ApiResponseError:
            return


class RemoveSubscriptionApiRequest(object):
    """Remove subscription api request class."""

    def __init__(self):
        self._subscription_id = None
        self._response_code = 404
        self._response_error = 'Subscription was not found.'

    def subscription_id(self, subscription_id):
        self._subscription_id = subscription_id

    def response_code(self, code):
        self._response_code = code

    def response_error(self, error):
        self._response_error = error

    def extract(self):
        return {'subscription_id': self._subscription_id,
                'response_code': self._response_code,
                'response_error': self._response_error}


class ApiRequestError(TransportError):
    """Api request error."""
