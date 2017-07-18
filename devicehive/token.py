from devicehive.api_object import ApiObject
from devicehive.api_request import ApiRequest
from devicehive.api_response import ApiResponseException


class Token(ApiObject):
    """Token class."""

    AUTHORIZATION_HEADER_NAME = 'Authorization'
    AUTHORIZATION_HEADER_VALUE_PREFIX = 'Bearer '

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
        api_request = ApiRequest(self._transport)
        if not api_request.websocket_transport():
            # TODO: remove.
            headers = {'Authorization': 'Bearer ' + self._access_token}
            self._authentication_params['headers'] = headers
            return
        api_request.set_action('authenticate')
        api_request.set('token', self._access_token)
        api_request.execute('Authentication failure')

    def _set_authentication_params(self, params):
        # TODO: remove method.
        for key in self._authentication_params:
            params[key] = self._authentication_params[key]

    def authorized_request(self, url, action, request, **params):
        # TODO: remove method.
        self._set_authentication_params(params)
        response = self._request(url, action, request.copy(), **params)
        if response.success() or response.code() != 401:
            return response
        self.authenticate()
        self._set_authentication_params(params)
        return self._request(url, action, request, **params)

    def _set_authorization_header(self, api_request):
        name = self.AUTHORIZATION_HEADER_NAME
        value = self.AUTHORIZATION_HEADER_VALUE_PREFIX + self._access_token
        api_request.set_header(name, value)

    def execute_authorized_request(self, api_request, exception_message):
        self._set_authorization_header(api_request)
        try:
            return api_request.execute(exception_message)
        except ApiResponseException as api_response_exception:
            if api_response_exception.code() != 401:
                raise
            self.authenticate()
            self._set_authorization_header(api_request)
            return api_request.execute(exception_message)

    def access_token(self):
        return self._access_token

    def create(self, user_id, expiration=None, actions=None, network_ids=None,
               device_ids=None):
        payload = {'userId': user_id}
        if expiration:
            payload['expiration'] = expiration
        if actions:
            payload['actions'] = actions
        if network_ids:
            payload['networkIds'] = network_ids
        if device_ids:
            payload['deviceIds'] = device_ids
        api_request = ApiRequest(self._transport)
        api_request.set_post_method()
        api_request.set_url('token/create')
        api_request.set_action('token/create')
        api_request.set('payload', payload, True)
        exception_message = 'Token refresh failure'
        tokens = self.execute_authorized_request(api_request,
                                                 exception_message)
        return {'refresh_token': tokens['refreshToken'],
                'access_token': tokens['accessToken']}

    def refresh(self):
        api_request = ApiRequest(self._transport)
        api_request.set_post_method()
        api_request.set_url('token/refresh')
        api_request.set_action('token/refresh')
        api_request.set('refreshToken', self._refresh_token)
        exception_message = 'Token refresh failure'
        tokens = api_request.execute(exception_message)
        self._access_token = tokens['accessToken']

    def authenticate(self):
        if self._refresh_token:
            self.refresh()
        else:
            self._login()
        self._authenticate()
