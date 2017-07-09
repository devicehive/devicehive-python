from devicehive.api_object import ApiObject


class Command(ApiObject):
    """Command class."""

    DEVICE_ID_KEY = 'deviceId'
    ID_KEY = 'id'
    USER_ID_KEY = 'userId'
    COMMAND_KEY = 'command'
    PARAMETERS_KEY = 'parameters'
    LIFETIME_KEY = 'lifetime'
    TIMESTAMP_KEY = 'timestamp'
    STATUS_KEY = 'status'
    RESULT_KEY = 'result'

    def __init__(self, transport, token, command):
        ApiObject.__init__(self, transport)
        self._token = token
        self._device_id = command[self.DEVICE_ID_KEY]
        self._id = command[self.ID_KEY]
        self._user_id = command[self.USER_ID_KEY]
        self._command = command[self.COMMAND_KEY]
        self._parameters = command[self.PARAMETERS_KEY]
        self._lifetime = command[self.LIFETIME_KEY]
        self._timestamp = command[self.TIMESTAMP_KEY]
        self.status = command[self.STATUS_KEY]
        self.result = command[self.RESULT_KEY]

    def device_id(self):
        return self._device_id

    def id(self):
        return self._id

    def user_id(self):
        return self._user_id

    def command(self):
        return self._command

    def parameters(self):
        return self._parameters

    def lifetime(self):
        return self._lifetime

    def timestamp(self):
        return self._timestamp

    def save(self):
        url = 'device/%s/command/%s' % (self._device_id, self._id)
        action = 'command/update'
        command = {'status': self.status, 'result': self.result}
        request = {'deviceId': self._device_id,
                   'commandId': self._id,
                   'command': command}
        params = {'method': 'PUT', 'request_key': 'command'}
        response = self._token.authorized_request(url, action, request,
                                                  **params)
        self._ensure_success_response(response, 'Command save failure')
