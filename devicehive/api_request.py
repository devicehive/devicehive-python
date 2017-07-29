from devicehive.api_response import ApiResponse
from devicehive.api_response import ApiResponseError
from devicehive.transports.transport import TransportError
import uuid


class ApiRequest(object):
    """Api request class."""

    def __init__(self, api):
        self._api = api
        self._action = None
        self._request = {}
        self._params = {'subscription_requests': [],
                        'remove_subscription_requests': False,
                        'method': 'GET',
                        'url': None,
                        'request_delete_keys': [],
                        'request_key': None,
                        'params': {},
                        'headers': {},
                        'response_key': None}

    @staticmethod
    def _uuid():
        return str(uuid.uuid1())

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

    def add_subscription_request(self, subscription_api_request):
        subscription_request = subscription_api_request.extract()
        self._params['subscription_requests'].append(subscription_request)

    def remove_subscription_requests(self):
        self._params['remove_subscription_requests'] = True

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

    def response_key(self, response_key):
        self._params['response_key'] = response_key

    def execute(self, error_message):
        response = self._api.transport.request(self._uuid(), self._action,
                                               self._request.copy(),
                                               **self._params)
        api_response = ApiResponse(response, self._params['response_key'])
        if api_response.success:
            return api_response.response
        raise ApiResponseError(error_message, self._api.transport.name,
                               api_response.code, api_response.error)


class AuthApiRequest(ApiRequest):
    """Auth api request class."""

    def execute(self, error_message):
        self.header(*self._api.token.auth_header)
        try:
            return ApiRequest.execute(self, error_message)
        except ApiResponseError as api_response_error:
            if api_response_error.code != 401:
                raise
        self._api.token.auth()
        self.header(*self._api.token.auth_header)
        return ApiRequest.execute(self, error_message)


class SubscriptionApiRequest(object):
    """Subscription api request class."""

    def __init__(self):
        self._action = None
        self._request = {}
        self._params = {'method': 'GET',
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

    def response_key(self, response_key):
        self._params['response_key'] = response_key

    def params_timestamp_key(self, params_timestamp_key):
        self._params['params_timestamp_key'] = params_timestamp_key

    def response_timestamp_key(self, response_timestamp_key):
        self._params['response_timestamp_key'] = response_timestamp_key

    def extract(self):
        return self._action, self._request, self._params


class AuthSubscriptionApiRequest(SubscriptionApiRequest):
    """Auth subscription api request class."""

    def __init__(self, api):
        SubscriptionApiRequest.__init__(self)
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


class ApiRequestError(TransportError):
    """Api request error."""
