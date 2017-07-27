from devicehive.api_request import ApiRequest
from devicehive.api_response import ApiResponseError


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
        if not api_request.websocket_transport:
            return
        api_request.action('authenticate')
        api_request.set('token', self._access_token)
        api_request.execute('Authentication failure')

    @property
    def authorization_header(self):
        name = self.AUTHORIZATION_HEADER_NAME
        value = self.AUTHORIZATION_HEADER_VALUE_PREFIX + self._access_token
        return name, value

    def execute_api_request(self, api_request, error_message):
        api_request.header(*self.authorization_header)
        try:
            return api_request.execute(error_message)
        except ApiResponseError as api_response_error:
            if api_response_error.code != 401:
                raise
        self.authenticate()
        api_request.header(*self.authorization_header)
        return api_request.execute(error_message)

    def access_token(self):
        return self._access_token

    def refresh(self):
        api_request = ApiRequest(self._transport)
        api_request.method('POST')
        api_request.url('token/refresh')
        api_request.action('token/refresh')
        api_request.set('refreshToken', self._refresh_token)
        tokens = api_request.execute('Token refresh failure')
        self._access_token = tokens['accessToken']

    def authenticate(self):
        if self._refresh_token:
            self.refresh()
        else:
            self._login()
        self._authenticate()
