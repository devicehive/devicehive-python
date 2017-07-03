class Request(object):
    """Request class."""

    def __init__(self, url, action, request, **params):
        self.action = action
        self.request = request
        self.params = params
        self.params['url'] = url


class Response(object):
    """Response class."""

    def __init__(self, response):
        self.action = response.pop('action')
        self.is_success = response.pop('status') == 'success'
        self.code = response.pop('code', None)
        self.error = response.pop('error', None)
        self.data = response


class ApiObject(object):
    """Api object class."""

    def __init__(self, transport):
        self._transport = transport

    def _is_http_transport(self):
        return self._transport.name == 'http'

    def _is_websocket_transport(self):
        return self._transport.name == 'websocket'

    def _request(self, url, action, request, **params):
        req = Request(url, action, request, **params)
        resp = self._transport.request(req.action, req.request, **req.params)
        return Response(resp)


class Authentication(ApiObject):
    """Authentication class."""

    def __init__(self, transport, refresh_toke, access_token=None):
        ApiObject.__init__(self, transport)
        self._refresh_token = refresh_toke
        self._access_token = access_token
        self._header_name = 'Authorization'
        self._header_value_prefix = 'Barer '
        self._params = {}

    def refresh_token(self):
        url = 'token/refresh'
        action = url
        request = {'refreshToken': self._refresh_token}
        params = {'method': 'POST',
                  'merge_data': True}
        response = self._request(url, action, request, **params)
        self._access_token = response.data['accessToken']

    def access_token_is_set(self):
        return self._access_token is not None

    def authenticate(self):
        if self._is_websocket_transport():
            url = None
            action = 'authenticate'
            request = {'token': self._access_token}
            params = {}
            response = self._request(url, action, request, **params)
            assert response.is_success, 'Authentication failure'
            return
        header_value = self._header_value_prefix + self._access_token
        self._params = {'headers': {self._header_name: header_value}}

    def params(self):
        return self._params


class Api(object):
    """Api class."""

    def __init__(self, transport):
        self._transport = transport
        self._authentication = None

    def authenticate(self, refresh_token, access_token):
        self._authentication = Authentication(self._transport, refresh_token,
                                              access_token)
        if not self._authentication.access_token_is_set():
            self._authentication.refresh_token()
        self._authentication.authenticate()
