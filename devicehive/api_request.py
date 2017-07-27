from devicehive.api_response import ApiResponse
from devicehive.api_response import ApiResponseError
from devicehive.transports.transport import TransportError


class ApiRequest(object):
    """Api request class."""

    def __init__(self, transport):
        self._transport = transport
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

    @property
    def http_transport(self):
        return self._transport.name == 'http'

    @property
    def websocket_transport(self):
        return self._transport.name == 'websocket'

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
        response = self._transport.request(self._action, self._request.copy(),
                                           **self._params)
        api_response = ApiResponse(response, self._params['response_key'])
        if api_response.success:
            return api_response.response
        raise ApiResponseError(error_message, self._transport.name,
                               api_response.code, api_response.error)


class AuthApiRequest(ApiRequest):
    """Auth api request class."""

    def __init__(self, transport, token):
        ApiRequest.__init__(self, transport)
        self._token = token

    def execute(self, error_message):
        self.header(*self._token.auth_header)
        try:
            ApiRequest.execute(self, error_message)
        except ApiResponseError as api_response_error:
            if api_response_error.code != 401:
                raise
        self._token.auth()
        self.header(*self._token.auth_header)
        return ApiRequest.execute(self, error_message)


class ApiRequestError(TransportError):
    """Api request error."""
