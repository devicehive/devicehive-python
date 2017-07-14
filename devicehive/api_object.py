class Request(object):
    """Request class."""

    def __init__(self, url, action, request, **params):
        self._action = action
        self._request = request
        self._params = params
        self._params['url'] = url

    def action(self):
        return self._action

    def request(self):
        return self._request

    def params(self):
        return self._params


class Response(object):
    """Response class."""

    def __init__(self, response):
        self._id = response.pop('requestId')
        self._action = response.pop('action')
        self._success = response.pop('status') == 'success'
        self._code = response.pop('code', None)
        self._error = response.pop('error', None)
        self._response = response

    def id(self):
        return self._id

    def action(self):
        return self._action

    def success(self):
        return self._success

    def code(self):
        return self._code

    def error(self):
        return self._error

    def response(self, key=None):
        if key:
            return self._response[key]
        return self._response


class ApiObject(object):
    """Api object class."""

    def __init__(self, transport):
        self._transport = transport
        self._transport_name = self._transport.name()

    def _http_transport(self):
        return self._transport_name == 'http'

    def _websocket_transport(self):
        return self._transport_name == 'websocket'

    def _request(self, url, action, request, **params):
        request = Request(url, action, request, **params)
        response = self._transport.request(request.action(), request.request(),
                                           **request.params())
        return Response(response)

    def _ensure_success_response(self, response, message):
        if not response.success():
            raise ApiObjectResponseException(message, self._transport_name,
                                             response.code(), response.error())

    def _ensure_http_transport(self):
        if not self._http_transport():
            raise ApiObjectException('Implemented only for http transport')


class ApiObjectException(Exception):
    """Api object exception."""
    pass


class ApiObjectResponseException(ApiObjectException):
    """Api object response exception."""

    def __init__(self, message, transport_name, code, error):
        message = '%s. Transport: %s. Code: %s. Error: %s.' % (message,
                                                               transport_name,
                                                               code, error)
        ApiObjectException.__init__(self, message)
        self.message = message
        self.transport_name = transport_name
        self.code = code
        self.error = error
