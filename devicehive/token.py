from devicehive.api_request import ApiRequest
from devicehive.api_response import ApiResponseError


class Token(object):
    """Token class."""

    AUTH_HEADER_NAME = 'Authorization'
    AUTH_HEADER_VALUE_PREFIX = 'Bearer '

    def __init__(self, transport, auth):
        self._transport = transport
        self._login = auth.get('login')
        self._password = auth.get('password')
        self._refresh_token = auth.get('refresh_token')
        self._access_token = auth.get('access_token')

    def _login(self):
        # TODO: implement token/login request.
        # Set self._refresh_token and self._access_token after success login.
        pass

    def _auth(self):
        api_request = ApiRequest(self._transport)
        if not api_request.websocket_transport:
            return
        api_request.action('authenticate')
        api_request.set('token', self._access_token)
        api_request.execute('Authentication failure')

    @property
    def access_token(self):
        return self._access_token

    @property
    def auth_header(self):
        auth_header_name = self.AUTH_HEADER_NAME
        auth_header_value = self.AUTH_HEADER_VALUE_PREFIX + self._access_token
        return auth_header_name, auth_header_value

    def execute_auth_api_request(self, api_request, error_message):
        api_request.header(*self.auth_header)
        try:
            return api_request.execute(error_message)
        except ApiResponseError as api_response_error:
            if api_response_error.code != 401:
                raise
        self.auth()
        api_request.header(*self.auth_header)
        return api_request.execute(error_message)

    def refresh(self):
        api_request = ApiRequest(self._transport)
        api_request.method('POST')
        api_request.url('token/refresh')
        api_request.action('token/refresh')
        api_request.set('refreshToken', self._refresh_token)
        tokens = api_request.execute('Token refresh failure')
        self._access_token = tokens['accessToken']

    def auth(self):
        if self._refresh_token:
            self.refresh()
        else:
            self._login()
        self._auth()
