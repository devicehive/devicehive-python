from devicehive.transports.transport import TransportError


class ApiResponse(object):
    """Api response class."""

    SUCCESS_STATUS = 'success'
    ID_KEY = 'requestId'
    ACTION_KEY = 'action'
    STATUS_KEY = 'status'
    CODE_KEY = 'code'
    ERROR_KEY = 'error'

    def __init__(self, response, key=None):
        self._id = response.pop(self.ID_KEY)
        self._action = response.pop(self.ACTION_KEY)
        self._success = response.pop(self.STATUS_KEY) == self.SUCCESS_STATUS
        self._code = response.pop(self.CODE_KEY, None)
        self._error = response.pop(self.ERROR_KEY, None)
        if not key:
            self._response = response
            return
        self._response = response.get(key)

    @property
    def id(self):
        return self._id

    @property
    def action(self):
        return self._action

    @property
    def success(self):
        return self._success

    @property
    def code(self):
        return self._code

    @property
    def error(self):
        return self._error

    @property
    def response(self):
        return self._response


class ApiResponseError(TransportError):
    """Api response error."""

    def __init__(self, message, transport_name, code, error):
        message = '%s Transport: %s. Code: %s. Error: %s' % (message,
                                                             transport_name,
                                                             code, error)
        super(ApiResponseError, self).__init__(message)
        self._transport_name = transport_name
        self._code = code
        self._error = error

    @property
    def transport_name(self):
        return self._transport_name

    @property
    def code(self):
        return self._code

    @property
    def error(self):
        return self._error
