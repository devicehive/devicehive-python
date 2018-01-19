# Copyright (C) 2018 DataArt
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================


from devicehive.api_request import ApiRequest
from devicehive.api_request import ApiRequestError


class Token(object):
    """Token class."""

    AUTH_HEADER_NAME = 'Authorization'
    AUTH_HEADER_VALUE_PREFIX = 'Bearer '

    def __init__(self, api, auth):
        self._api = api
        self._login = auth.get('login')
        self._password = auth.get('password')
        self._refresh_token = auth.get('refresh_token')
        self._access_token = auth.get('access_token')

    def _auth(self):
        api_request = ApiRequest(self._api)
        if not api_request.websocket_transport:
            return
        api_request.action('authenticate')
        api_request.set('token', self._access_token)
        api_request.execute('Authentication failure.')

    def _tokens(self):
        api_request = ApiRequest(self._api)
        api_request.method('POST')
        api_request.url('token')
        api_request.action('token')
        api_request.set('login', self._login)
        api_request.set('password', self._password)
        tokens = api_request.execute('Login failure.')
        self._refresh_token = tokens['refreshToken']
        self._access_token = tokens['accessToken']

    @property
    def access_token(self):
        return self._access_token

    @property
    def auth_header(self):
        auth_header_name = self.AUTH_HEADER_NAME
        auth_header_value = self.AUTH_HEADER_VALUE_PREFIX + self._access_token
        return auth_header_name, auth_header_value

    def refresh(self):
        if not self._refresh_token:
            raise TokenError('Can\'t refresh token without "refresh_token"')
        api_request = ApiRequest(self._api)
        api_request.method('POST')
        api_request.url('token/refresh')
        api_request.action('token/refresh')
        api_request.set('refreshToken', self._refresh_token)
        tokens = api_request.execute('Token refresh failure.')
        self._access_token = tokens['accessToken']

    def auth(self):
        if self._refresh_token:
            self.refresh()
            self._auth()
            return
        if self._access_token:
            self._auth()
            return
        if self._login and self._password:
            self._tokens()
            self._auth()
            return
        if self._login:
            raise TokenError('Password required.')
        if self._password:
            raise TokenError('Login required.')


class TokenError(ApiRequestError):
    """Token error."""
