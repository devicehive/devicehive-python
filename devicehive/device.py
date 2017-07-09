from devicehive.api_object import ApiObject
from devicehive.command import Command


class Device(ApiObject):
    """Device class."""

    ID_KEY = 'id'
    NAME_KEY = 'name'
    DATA_KEY = 'data'
    NETWORK_ID_KEY = 'networkId'
    IS_BLOCKED_KEY = 'isBlocked'

    def __init__(self, transport, token, device=None):
        ApiObject.__init__(self, transport)
        self._token = token
        self._id = None
        self.name = None
        self.data = None
        self.network_id = None
        self.is_blocked = None
        if device:
            self._init(device)

    def _init(self, device):
        self._id = device[self.ID_KEY]
        self.name = device[self.NAME_KEY]
        self.data = device[self.DATA_KEY]
        self.network_id = device[self.NETWORK_ID_KEY]
        self.is_blocked = device[self.IS_BLOCKED_KEY]

    def id(self):
        return self._id

    def get(self, device_id):
        url = 'device/%s' % device_id
        action = 'device/get'
        request = {'deviceId': device_id}
        params = {'request_delete_keys': ['deviceId'], 'response_key': 'device'}
        response = self._token.authorized_request(url, action, request,
                                                  **params)
        self._ensure_success_response(response, 'Device get failure')
        device = response.response('device')
        self._init(device)

    def save(self):
        url = 'device/%s' % self._id
        action = 'device/save'
        device = {self.ID_KEY: self._id,
                  self.NAME_KEY: self.name,
                  self.DATA_KEY: self.data,
                  self.NETWORK_ID_KEY: self.network_id,
                  self.IS_BLOCKED_KEY: self.is_blocked}
        request = {'deviceId': self._id, 'device': device}
        params = {'method': 'PUT', 'request_key': 'device'}
        response = self._token.authorized_request(url, action, request,
                                                  **params)
        self._ensure_success_response(response, 'Device save failure')

    def remove(self):
        # TODO: implement websocket support when API will be added.
        self._ensure_http_transport()
        url = 'device/%s' % self._id
        action = None
        request = {}
        params = {'method': 'DELETE'}
        response = self._token.authorized_request(url, action, request,
                                                  **params)
        self._ensure_success_response(response, 'Device remove failure')
        self._id = None
        self.name = None
        self.data = None
        self.network_id = None
        self.is_blocked = None

    def list_commands(self, start=None, end=None, command=None, status=None,
                      sort_field=None, sort_order=None, take=None, skip=None):
        # TODO: implement websocket support when API will be added.
        self._ensure_http_transport()
        url = 'device/%s/command' % self._id
        action = None
        request = {}
        params = {'response_key': 'commands', 'params': {}}
        if start:
            params['params']['start'] = start
        if end:
            params['params']['end'] = end
        if command:
            params['params']['command'] = command
        if status:
            params['params']['status'] = status
        if sort_field:
            params['params']['sortField'] = sort_field
        if sort_order:
            params['params']['sortOrder'] = sort_order
        if take:
            params['params']['take'] = take
        if skip:
            params['params']['skip'] = skip
        response = self._token.authorized_request(url, action, request,
                                                  **params)
        self._ensure_success_response(response, 'List device commands failure')
        commands = response.response('commands')
        return [Command(self._transport, self._token, command)
                for command in commands]

    def send_command(self, command_name, parameters=None, lifetime=None,
                     timestamp=None, status=None, result=None):
        url = 'device/%s/command' % self._id
        action = 'command/insert'
        command = {Command.COMMAND_KEY: command_name}
        if parameters:
            command[Command.PARAMETERS_KEY] = parameters
        if lifetime:
            command[Command.LIFETIME_KEY] = lifetime
        if timestamp:
            command[Command.TIMESTAMP_KEY] = timestamp
        if status:
            command[Command.STATUS_KEY] = status
        if result:
            command[Command.RESULT_KEY] = result
        request = {'deviceId': self._id, 'command': command}
        params = {'method': 'POST',
                  'request_key': 'command',
                  'response_key': 'command'}
        response = self._token.authorized_request(url, action, request,
                                                  **params)
        self._ensure_success_response(response, 'Command send failure')
        command = response.response('command')
        command[Command.DEVICE_ID_KEY] = self._id
        command[Command.COMMAND_KEY] = command_name
        command[Command.PARAMETERS_KEY] = parameters
        command[Command.LIFETIME_KEY] = lifetime
        command[Command.STATUS_KEY] = status
        command[Command.RESULT_KEY] = result
        return Command(self._transport, self._token, command)
