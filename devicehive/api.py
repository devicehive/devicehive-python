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

    def __init__(self, transport):
        self._transport = transport

    def is_http_transport(self):
        return self._transport.name == 'http'

    def is_websocket_transport(self):
        return self._transport.name == 'websocket'

    def _request(self, url, action, request, **params):
        req = Request(url, action, request, **params)
        resp = self._transport.request(req.action, req.request, **req.params)
        return Response(resp)


class Token(ApiObject):

    def __init__(self, transport, refresh_toke, access_token=None):
        ApiObject.__init__(self, transport)
        self._refresh_token = refresh_toke
        self._access_token = access_token

    def refresh(self):
        url = 'token/refresh'
        action = url
        request = {'refreshToken': self._refresh_token}
        params = {'method': 'POST',
                  'merge_data': True}
        response = self._request(url, action, request, **params)
        self._access_token = response.data['accessToken']

    def access_token(self):
        return self._access_token


class Api(object):
    """Api class."""

    def __init__(self, transport):
        self._transport = transport

    def token(self, refresh_token, access_token):
        return Token(self._transport, refresh_token, access_token)
