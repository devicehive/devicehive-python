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
        request = ApiRequest(self._transport)
        request.set_post_method()
        request.set_url('token/refresh')
        request.set_action('token/refresh')
        request.set('refreshToken', self._refresh_token)
        response = request.execute('Token refresh failure')
        self._access_token = response.value('accessToken')

    def authenticate(self):
        if self._refresh_token:
            self.refresh()
        else:
            self._login()
        self._authenticate()
