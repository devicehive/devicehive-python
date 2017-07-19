class ApiException(Exception):
    """Api exception."""


class ApiRequestException(ApiException):
    """Api request exception."""


class ApiResponseException(ApiException):
    """Api response exception."""

    def __init__(self, message, transport_name, code, error):
        message = '%s. Transport: %s. Code: %s. Error: %s.' % (message,
                                                               transport_name,
                                                               code, error)
        Exception.__init__(self, message)
        self._transport_name = transport_name
        self._code = code
        self._error = error

    def transport_name(self):
        return self._transport_name

    def code(self):
        return self._code

    def error(self):
        return self._error


class DeviceException(ApiException):
    """Device exception."""
