from devicehive.api_object import ApiObject


class Token(ApiObject):
    """Token class."""

    def __init__(self, transport, authentication):
        ApiObject.__init__(self, transport)
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
        if self._websocket_transport():
            url = None
            action = 'authenticate'
            request = {'token': self._access_token}
            params = {}
            response = self._request(url, action, request, **params)
            self._ensure_success_response(response, 'Authentication failure')
            return
        headers = {'Authorization': 'Bearer ' + self._access_token}
        self._authentication_params['headers'] = headers

    def authorized_request(self, url, action, request, **params):
        for key in self._authentication_params:
            params[key] = self._authentication_params[key]
        response = self._request(url, action, request, **params)
        if response.success():
            return response
        if response.code() == 401:
            self.authenticate()
        return self._request(url, action, request, **params)

    def access_token(self):
        return self._access_token

    def create(self, user_id, expiration, actions, network_ids, device_ids):
        # TODO: implement websocket support when API will be added.
        self._ensure_http_transport()
        url = 'token/create'
        action = None
        request = {'userId': user_id}
        if expiration:
            request['expiration'] = expiration
        if actions:
            request['actions'] = actions
        if network_ids:
            request['networkIds'] = network_ids
        if device_ids:
            request['deviceIds'] = device_ids
        params = {'method': 'POST'}
        response = self.authorized_request(url, action, request, **params)
        self._ensure_success_response(response, 'Token create failure')
        return {'refresh_token': response.response('refreshToken'),
                'access_token': response.response('accessToken')}

    def refresh(self):
        url = 'token/refresh'
        action = url
        request = {'refreshToken': self._refresh_token}
        params = {'method': 'POST'}
        response = self._request(url, action, request, **params)
        self._ensure_success_response(response, 'Token refresh failure')
        self._access_token = response.response('accessToken')

    def authenticate(self):
        if self._refresh_token:
            self.refresh()
        else:
            self._login()
        self._authenticate()
