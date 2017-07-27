from devicehive.api_request import ApiRequest
from devicehive.api_subscribe_request import ApiAuthSubscribeRequest
from devicehive.command import Command
from devicehive.notification import Notification
from devicehive.api_request import ApiRequestError


class Device(object):
    """Device class."""

    ID_KEY = 'id'
    NAME_KEY = 'name'
    DATA_KEY = 'data'
    NETWORK_ID_KEY = 'networkId'
    IS_BLOCKED_KEY = 'isBlocked'

    def __init__(self, transport, token, device=None):
        self._transport = transport
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

    def _ensure_exists(self):
        if self._id:
            return
        raise DeviceError('Does not exist.')

    @property
    def id(self):
        return self._id

    def get(self, device_id):
        api_request = ApiRequest(self._transport)
        api_request.url('device/{deviceId}', deviceId=device_id)
        api_request.action('device/get')
        api_request.response_key('device')
        device = self._token.execute_auth_api_request(api_request,
                                                      'Device get failure')
        self._init(device)

    def save(self):
        self._ensure_exists()
        device = {self.ID_KEY: self._id,
                  self.NAME_KEY: self.name,
                  self.DATA_KEY: self.data,
                  self.NETWORK_ID_KEY: self.network_id,
                  self.IS_BLOCKED_KEY: self.is_blocked}
        api_request = ApiRequest(self._transport)
        api_request.method('PUT')
        api_request.url('device/{deviceId}', deviceId=self._id)
        api_request.action('device/save')
        api_request.set('device', device, True)
        self._token.execute_auth_api_request(api_request, 'Device save failure')

    def remove(self):
        self._ensure_exists()
        api_request = ApiRequest(self._transport)
        api_request.method('DELETE')
        api_request.url('device/{deviceId}', deviceId=self._id)
        api_request.action('device/delete')
        self._token.execute_auth_api_request(api_request,
                                             'Device remove failure')
        self._id = None
        self.name = None
        self.data = None
        self.network_id = None
        self.is_blocked = None

    def subscribe_commands(self, names=None, limit=None, timestamp=None):
        insert_api_auth_subscribe_request = ApiAuthSubscribeRequest(self._token)
        insert_api_auth_subscribe_request.action('command/insert')
        insert_api_auth_subscribe_request.url('device/{deviceId}/command/poll',
                                              deviceId=self._id)
        insert_api_auth_subscribe_request.response_key('command')
        update_api_auth_subscribe_request = ApiAuthSubscribeRequest(self._token)
        update_api_auth_subscribe_request.action('command/update')
        update_api_auth_subscribe_request.url('device/{deviceId}/command/poll',
                                              deviceId=self._id)
        update_api_auth_subscribe_request.param('returnUpdatedCommands', True)
        update_api_auth_subscribe_request.response_key('command')
        update_api_auth_subscribe_request.response_timestamp_key('lastUpdated')
        api_request = ApiRequest(self._transport)
        api_request.action('command/subscribe')
        api_request.add_subscribe_request(insert_api_auth_subscribe_request)
        api_request.add_subscribe_request(update_api_auth_subscribe_request)
        response = api_request.execute('Subscribe commands failure')
        return response['subscriptionId']

    def list_commands(self, start=None, end=None, command=None, status=None,
                      sort_field=None, sort_order=None, take=None, skip=None):
        self._ensure_exists()
        api_request = ApiRequest(self._transport)
        api_request.url('device/{deviceId}/command', deviceId=self._id)
        api_request.action('command/list')
        api_request.param('start', start)
        api_request.param('end', end)
        api_request.param('command', command)
        api_request.param('status', status)
        api_request.param('sortField', sort_field)
        api_request.param('sortOrder', sort_order)
        api_request.param('take', take)
        api_request.param('skip', skip)
        api_request.response_key('commands')
        commands = self._token.execute_auth_api_request(api_request,
                                                        'List commands failure')
        return [Command(self._transport, self._token, command)
                for command in commands]

    def send_command(self, command_name, parameters=None, lifetime=None,
                     timestamp=None, status=None, result=None):
        self._ensure_exists()
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
        api_request = ApiRequest(self._transport)
        api_request.method('POST')
        api_request.url('device/{deviceId}/command', deviceId=self._id)
        api_request.action('command/insert')
        api_request.set('command', command, True)
        api_request.response_key('command')
        command = self._token.execute_auth_api_request(api_request,
                                                       'Command send failure')
        command[Command.DEVICE_ID_KEY] = self._id
        command[Command.COMMAND_KEY] = command_name
        command[Command.PARAMETERS_KEY] = parameters
        command[Command.LIFETIME_KEY] = lifetime
        command[Command.STATUS_KEY] = status
        command[Command.RESULT_KEY] = result
        return Command(self._transport, self._token, command)

    def list_notifications(self, start=None, end=None, notification=None,
                           sort_field=None, sort_order=None, take=None,
                           skip=None):
        self._ensure_exists()
        api_request = ApiRequest(self._transport)
        api_request.url('device/{deviceId}/notification', deviceId=self._id)
        api_request.action('notification/list')
        api_request.param('start', start)
        api_request.param('end', end)
        api_request.param('notification', notification)
        api_request.param('sortField', sort_field)
        api_request.param('sortOrder', sort_order)
        api_request.param('take', take)
        api_request.param('skip', skip)
        api_request.response_key('notifications')
        error_message = 'List notifications failure'
        notifications = self._token.execute_auth_api_request(api_request,
                                                             error_message)
        return [Notification(notification) for notification in notifications]

    def send_notification(self, notification_name, parameters=None,
                          timestamp=None):
        self._ensure_exists()
        notification = {'notification': notification_name}
        if parameters:
            notification['parameters'] = parameters
        if timestamp:
            notification['timestamp'] = timestamp
        api_request = ApiRequest(self._transport)
        api_request.method('POST')
        api_request.url('device/{deviceId}/notification', deviceId=self._id)
        api_request.action('notification/insert')
        api_request.set('notification', notification, True)
        api_request.response_key('notification')
        error_message = 'Notification send failure'
        notification = self._token.execute_auth_api_request(api_request,
                                                            error_message)
        notification[Notification.DEVICE_ID_KEY] = self._id
        notification[Notification.NOTIFICATION_KEY] = notification_name
        notification[Notification.PARAMETERS_KEY] = parameters
        return Notification(notification)


class DeviceError(ApiRequestError):
    """Device error."""
