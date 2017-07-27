from devicehive.api_request import ApiRequest


class Command(object):
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
        self._transport = transport
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

    @property
    def device_id(self):
        return self._device_id

    @property
    def id(self):
        return self._id

    @property
    def user_id(self):
        return self._user_id

    @property
    def command(self):
        return self._command

    @property
    def parameters(self):
        return self._parameters

    @property
    def lifetime(self):
        return self._lifetime

    @property
    def timestamp(self):
        return self._timestamp

    def save(self):
        command = {self.STATUS_KEY: self.status,
                   self.RESULT_KEY: self.result}
        api_request = ApiRequest(self._transport)
        api_request.method('PUT')
        api_request.url('device/{deviceId}/command/{commandId}',
                        deviceId=self._device_id, commandId=self._id)
        api_request.action('command/update')
        api_request.set('command', command, True)
        self._token.execute_api_request(api_request, 'Command save failure')
