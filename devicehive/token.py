from devicehive.api_request import ApiRequest
from devicehive.api_response import ApiResponseException


class Token(object):
    """Token class."""

    AUTHORIZATION_HEADER_NAME = 'Authorization'
    AUTHORIZATION_HEADER_VALUE_PREFIX = 'Bearer '

    def __init__(self, transport, authentication):
        self._transport = transport
        self._login = authentication.get('login')
        self._password = authentication.get('password')
        self._refresh_token = authentication.get('refresh_token')
        self._access_token = authentication.get('access_token')

    def _login(self):
        # TODO: implement token/login request.
        # Set self._refresh_token and self._access_token after success login.
        pass

    def _authenticate(self):
        api_request = ApiRequest(self._transport)
        if not api_request.websocket_transport():
            return
        api_request.set_action('authenticate')
        api_request.set('token', self._access_token)
        api_request.execute('Authentication failure')

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
