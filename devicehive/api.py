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
        self.id = response.pop('requestId')
        self.action = response.pop('action')
        self.is_success = response.pop('status') == 'success'
        self.code = response.pop('code', None)
        self.error = response.pop('error', None)
        self.data = response


class Api(object):
    """Api class."""

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


class Token(Api):
    """Token class."""

    def __init__(self, transport, authentication):
        Api.__init__(self, transport)
        self._login = authentication.get('login')
        self._password = authentication.get('password')
        self._refresh_token = authentication.get('refresh_token')
        self._access_token = authentication.get('access_token')
        self._authentication_params = {}

    def _login(self):
        # TODO: implement token/login request.
        # Set self._refresh_token and self._access_token after success login.
        pass

    def _authenticate(self):
        if self._is_websocket_transport():
            url = None
            action = 'authenticate'
            request = {'token': self._access_token}
            params = {}
            response = Api._request(self, url, action, request, **params)
            assert response.is_success, 'Authentication failure'
            return
        headers = {'Authorization': 'Bearer ' + self._access_token}
        self._authentication_params['headers'] = headers

    def authorized_request(self, url, action, request, **params):
        for key in self._authentication_params:
            params[key] = self._authentication_params[key]
        response = self._request(url, action, request, **params)
        if response.is_success:
            return response
        if response.code == 401:
            self.authenticate()
        return self._request(url, action, request, **params)

    def access_token(self):
        return self._access_token

    def create(self, user_id, expiration, actions, network_ids, device_ids):
        url = 'token/create'
        action = url
        request = {'userId': user_id}
        if expiration:
            request['expiration'] = expiration
        if actions:
            request['actions'] = actions
        if network_ids:
            request['networkIds'] = network_ids
        if device_ids:
            request['deviceIds'] = device_ids
        params = {'method': 'POST', 'merge_data': True}
        response = self.authorized_request(url, action, request, **params)
        assert response.is_success, 'Token create failure'
        return {'refresh_token': response.data['refreshToken'],
                'access_token': response.data['accessToken']}

    def refresh(self):
        url = 'token/refresh'
        action = url
        request = {'refreshToken': self._refresh_token}
        params = {'method': 'POST', 'merge_data': True}
        response = self._request(url, action, request, **params)
        assert response.is_success, 'Token refresh failure'
        self._access_token = response.data['accessToken']

    def authenticate(self):
        if self._refresh_token:
            self.refresh()
        else:
            self._login()
        self._authenticate()


class Device(Api):
    """Device class."""

    def __init__(self, transport, token):
        Api.__init__(self, transport)
        self._token = token
        self.id = None
        self.name = None
        self.data = None
        self.network_id = None
        self.is_blocked = None

    def get(self, device_id):
        url = 'device/%s' % device_id
        action = 'device/get'
        request = {}
        if self._is_websocket_transport():
            request['deviceId'] = device_id
        params = {'data_key': 'device'}
        response = self._token.authorized_request(url, action, request,
                                                  **params)
        if response.is_success:
            self.id = response.data['device']['id']
            self.name = response.data['device']['name']
            self.data = response.data['device']['data']
            self.network_id = response.data['device']['networkId']
            self.is_blocked = response.data['device']['isBlocked']
