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


class Info(Api):
    """Info class."""

    def get(self):
        url = 'info'
        action = 'server/info'
        request = {}
        params = {'data_key': 'info'}
        response = self._request(url, action, request, **params)
        assert response.is_success, 'Info get failure'
        info_data = response.data['info']
        info = {'api_version': info_data['apiVersion'],
                'server_timestamp': info_data['serverTimestamp']}
        if self._is_websocket_transport():
            info['rest_server_url'] = info_data['restServerUrl']
        else:
            info['web_socket_server_url'] = info_data['webSocketServerUrl']
        return info


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

    def __init__(self, transport, token, device_id=None, name=None, data=None,
                 network_id=None, is_blocked=None):
        Api.__init__(self, transport)
        self._token = token
        self.id = device_id
        self.name = name
        self.data = data
        self.network_id = network_id
        self.is_blocked = is_blocked

    def list(self, name=None, name_pattern=None, network_id=None,
             network_name=None, sort_field=None, sort_order=None, take=None,
             skip=None):
        url = 'device'
        action = 'device/list'
        request = {}
        params = {'data_key': 'devices', 'params': {}}
        if name:
            params['params']['name'] = name
        if name_pattern:
            params['params']['namePattern'] = name_pattern
        if network_id:
            params['params']['networkId'] = network_id
        if network_name:
            params['params']['networkName'] = network_name
        if sort_field:
            params['params']['sortField'] = sort_field
        if sort_order:
            params['params']['sortOrder'] = sort_order
        if take:
            params['params']['take'] = take
        if skip:
            params['params']['skip'] = skip
        response = self._token.authorized_request(url, action, request,
                                                  **params)
        assert response.is_success, 'List devices failure'
        devices = []
        for device in response.data['devices']:
            devices.append(Device(self._token, self._transport, device['id'],
                                  device['name'], device['data'],
                                  device['networkId'], device['isBlocked']))
        return devices

    def init(self, device_id):
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

    def save(self):
        url = 'device/%s' % self.id
        action = 'device/save'
        device = {'id': self.id,
                  'name': self.name,
                  'data': self.data,
                  'networkId': self.network_id,
                  'isBlocked': self.is_blocked}
        if self._is_websocket_transport():
            request = {'deviceId': self.id, 'device': device}
        else:
            request = device
        params = {'method': 'PUT'}
        response = self._token.authorized_request(url, action, request,
                                                  **params)
        assert response.is_success, 'Device save failure'

    def remove(self):
        url = 'device/%s' % self.id
        # TODO: implement websocket support when API will be added.
        action = None
        request = {}
        params = {'method': 'DELETE'}
        response = self._token.authorized_request(url, action, request,
                                                  **params)
        assert response.is_success, 'Device remove failure'
        self.id = None
        self.name = None
        self.data = None
        self.network_id = None
        self.is_blocked = None
