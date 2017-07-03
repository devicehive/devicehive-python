from devicehive.transport import Request
from devicehive.transport import Response


class Api(object):
    """Api class."""

    def __init__(self, transport):
        self._transport = transport

    def is_http_transport(self):
        return self._transport.name == 'http'

    def is_websocket_transport(self):
        return self._transport.name == 'websocket'

    def _request(self, url, action, request, **params):
        req = Request(url, action, request, **params)
        response = self._transport.request(req.action, req.request,
                                           **req.params)
        return Response(response)

    def refresh_token(self, refresh_token):
        url = 'token/refresh'
        action = url
        request = {'refreshToken': refresh_token}
        params = {'method': 'POST',
                  'merge_data': True}
        return self._request(url, action, request, **params)
