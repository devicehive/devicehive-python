from devicehive.api_request import ApiRequest
from devicehive.command import Command
from devicehive.notification import Notification
from devicehive.api_request import ApiRequestException


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
        raise DeviceException('Device does not exist.')

    @property
    def id(self):
        return self._id

    def get(self, device_id):
        api_request = ApiRequest(self._transport)
        api_request.url('device/{deviceId}', deviceId=device_id)
        api_request.action('device/get')
        api_request.response_key('device')
        exception_message = 'Device get failure'
        device = self._token.execute_authorized_request(api_request,
                                                        exception_message)
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
        exception_message = 'Device save failure'
        self._token.execute_authorized_request(api_request, exception_message)

    def remove(self):
        self._ensure_exists()
        api_request = ApiRequest(self._transport)
        api_request.method('DELETE')
        api_request.url('device/{deviceId}', deviceId=self._id)
        api_request.action('device/delete')
        exception_message = 'Device remove failure'
        self._token.execute_authorized_request(api_request, exception_message)
        self._id = None
        self.name = None
        self.data = None
        self.network_id = None
        self.is_blocked = None

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
        exception_message = 'List commands failure'
        commands = self._token.execute_authorized_request(api_request,
                                                          exception_message)
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
        exception_message = 'Command send failure'
        command = self._token.execute_authorized_request(api_request,
                                                         exception_message)
        command[Command.DEVICE_ID_KEY] = self._id
        command[Command.COMMAND_KEY] = command_name
        command[Command.PARAMETERS_KEY] = parameters
        command[Command.LIFETIME_KEY] = lifetime
        command[Command.STATUS_KEY] = status
        command[Command.RESULT_KEY] = result
        return Command(self._transport, self._token, command)

    def subscribe_commands(self, names=None, limit=None, timestamp=None):
        # TODO: implement after HTTP support will be ready.
        pass

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
        except_message = 'List notifications failure'
        notifications = self._token.execute_authorized_request(api_request,
                                                               except_message)
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
        exception_message = 'Notification send failure'
        notification = self._token.execute_authorized_request(api_request,
                                                              exception_message)
        notification[Notification.DEVICE_ID_KEY] = self._id
        notification[Notification.NOTIFICATION_KEY] = notification_name
        notification[Notification.PARAMETERS_KEY] = parameters
        return Notification(notification)


class DeviceException(ApiRequestException):
    """Device exception."""
