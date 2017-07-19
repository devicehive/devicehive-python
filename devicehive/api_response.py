from devicehive.api_exceptions import ApiResponseException


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

    def ensure_success(self, exception_message, transport_name):
        if self._success:
            return
        raise ApiResponseException(exception_message, transport_name,
                                   self._code, self._error)

    def response(self):
        return self._response
