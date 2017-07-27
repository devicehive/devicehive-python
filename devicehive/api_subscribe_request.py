from devicehive.api_response import ApiResponseError


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


class ApiSubscribeRequest(object):
    """Api subscribe request class."""

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


class ApiAuthSubscribeRequest(ApiSubscribeRequest):
    """Api auth subscribe request class."""

    def __init__(self, token):
        ApiSubscribeRequest.__init__(self)
        auth_header_name, auth_header_value = token.auth_header
        self._params['headers'][auth_header_name] = auth_header_value
        self._params['response_error_handler'] = response_error_handler
        self._params['response_error_handler_args'] = [token]
