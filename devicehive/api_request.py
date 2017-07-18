from devicehive.api_response import ApiResponse


class ApiRequest(object):
    """Api request class."""

    def __init__(self, transport):
        self._transport = transport
        self._transport_name = self._transport.name()
        self._url = None
        self._action = None
        self._request = {}
        self._params = {'request_delete_keys': [],
                        'params': {},
                        'headers': {}}

    def http_transport(self):
        return self._transport_name == 'http'

    def websocket_transport(self):
        return self._transport_name == 'websocket'

    def ensure_http_transport(self):
        if self.http_transport():
            return
        raise ApiRequestException('Implemented only for http transport')

    def url(self):
        return self._url

    def action(self):
        return self._action

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
            url = url.replace('{%s}' % key, args[key])
            self._request[key] = args[key]
            self._params['request_delete_keys'].append(key)
        self._url = url

    def set_action(self, action):
        self._action = action

    def set_header(self, name, value):
        self._params['headers'][name] = value

    def set_param(self, key, value):
        if not value:
            return
        self._request[key] = value
        self._params['request_delete_keys'].append(key)
        self._params['params'][key] = value

    def set(self, key, value):
        if not value:
            return
        self._request[key] = value

    def execute(self, error_message, request_key=None, response_key=None):
        self._params['url'] = self._url
        if request_key:
            self._params['request_key'] = request_key
        if response_key:
            self._params['response_key'] = response_key
        response = self._transport.request(self._action, self._request.copy(),
                                           **self._params)
        response = ApiResponse(response)
        response.ensure_success(error_message, self._transport_name)
        return response


class ApiRequestException(Exception):
    """Api request exception."""
    pass
