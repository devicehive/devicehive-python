from devicehive.api_response import ApiResponse
from devicehive.api_exception import ApiException


class ApiRequest(object):
    """Api request class."""

    def __init__(self, transport):
        self._transport = transport
        self._transport_name = self._transport.name()
        self._action = None
        self._request = {}
        self._params = {'method': 'GET',
                        'url': None,
                        'request_delete_keys': [],
                        'request_key': None,
                        'params': {},
                        'headers': {},
                        'response_key': None}

    def http_transport(self):
        return self._transport_name == 'http'

    def websocket_transport(self):
        return self._transport_name == 'websocket'

    def ensure_http_transport(self):
        if self.http_transport():
            return
        raise ApiRequestException('Implemented only for http transport')

    def set_action(self, action):
        self._action = action

    def set(self, key, value, request_key=False):
        if not value:
            return
        self._request[key] = value
        if not request_key:
            return
        self._params['request_key'] = key

    def set_get_method(self):
        self._params['method'] = 'GET'

    def set_post_method(self):
        self._params['method'] = 'POST'

    def set_put_method(self):
        self._params['method'] = 'PUT'

    def set_delete_method(self):
        self._params['method'] = 'DELETE'

    def set_url(self, url, **args):
        for key in args:
            url = url.replace('{%s}' % key, str(args[key]))
            self._request[key] = args[key]
            self._params['request_delete_keys'].append(key)
        self._params['url'] = url

    def set_param(self, key, value):
        if not value:
            return
        self._request[key] = value
        self._params['request_delete_keys'].append(key)
        self._params['params'][key] = value

    def set_header(self, name, value):
        self._params['headers'][name] = value

    def set_response_key(self, value):
        self._params['response_key'] = value

    def execute(self, exception_message):
        response = self._transport.request(self._action, self._request.copy(),
                                           **self._params)
        api_response = ApiResponse(response, self._params['response_key'])
        api_response.ensure_success(exception_message, self._transport_name)
        return api_response.response()


class ApiRequestException(ApiException):
    """Api request exception."""
    pass
