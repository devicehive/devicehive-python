from devicehive.api_request import ApiRequest
from devicehive.command import Command
from devicehive.notification import Notification


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

    def id(self):
        return self._id

    def get(self, device_id):
        api_request = ApiRequest(self._transport)
        api_request.set_url('device/{deviceId}', deviceId=device_id)
        api_request.set_action('device/get')
        api_request.set_response_key('device')
        exception_message = 'Device get failure'
        device = self._token.execute_authorized_request(api_request,
                                                        exception_message)
        self._init(device)

    def save(self):
        device = {self.ID_KEY: self._id,
                  self.NAME_KEY: self.name,
                  self.DATA_KEY: self.data,
                  self.NETWORK_ID_KEY: self.network_id,
                  self.IS_BLOCKED_KEY: self.is_blocked}
        api_request = ApiRequest(self._transport)
        api_request.set_put_method()
        api_request.set_url('device/{deviceId}', deviceId=self._id)
        api_request.set_action('device/save')
        api_request.set('device', device, True)
        exception_message = 'Device save failure'
        self._token.execute_authorized_request(api_request, exception_message)

    def remove(self):
        api_request = ApiRequest(self._transport)
        api_request.set_delete_method()
        api_request.set_url('device/{deviceId}', deviceId=self._id)
        api_request.set_action('device/delete')
        exception_message = 'Device remove failure'
        self._token.execute_authorized_request(api_request, exception_message)
        self._id = None
        self.name = None
        self.data = None
        self.network_id = None
        self.is_blocked = None

    def list_commands(self, start=None, end=None, command=None, status=None,
                      sort_field=None, sort_order=None, take=None, skip=None):
        api_request = ApiRequest(self._transport)
        api_request.set_url('device/{deviceId}/command', deviceId=self._id)
        api_request.set_action('command/list')
        api_request.set_param('start', start)
        api_request.set_param('end', end)
        api_request.set_param('command', command)
        api_request.set_param('status', status)
        api_request.set_param('sortField', sort_field)
        api_request.set_param('sortOrder', sort_order)
        api_request.set_param('take', take)
        api_request.set_param('skip', skip)
        api_request.set_response_key('commands')
        exception_message = 'List commands failure'
        commands = self._token.execute_authorized_request(api_request,
                                                          exception_message)
        return [Command(self._transport, self._token, command)
                for command in commands]

    def send_command(self, command_name, parameters=None, lifetime=None,
                     timestamp=None, status=None, result=None):
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
        api_request.set_post_method()
        api_request.set_url('device/{deviceId}/command', deviceId=self._id)
        api_request.set_action('command/insert')
        api_request.set('command', command, True)
        api_request.set_response_key('command')
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
        api_request = ApiRequest(self._transport)
        api_request.set_url('device/{deviceId}/notification', deviceId=self._id)
        api_request.set_action('notification/list')
        api_request.set_param('start', start)
        api_request.set_param('end', end)
        api_request.set_param('notification', notification)
        api_request.set_param('sortField', sort_field)
        api_request.set_param('sortOrder', sort_order)
        api_request.set_param('take', take)
        api_request.set_param('skip', skip)
        api_request.set_response_key('notifications')
        except_message = 'List notifications failure'
        notifications = self._token.execute_authorized_request(api_request,
                                                               except_message)
        return [Notification(notification) for notification in notifications]

    def send_notification(self, notification_name, parameters=None,
                          timestamp=None):
        notification = {'notification': notification_name}
        if parameters:
            notification['parameters'] = parameters
        if timestamp:
            notification['timestamp'] = timestamp
        api_request = ApiRequest(self._transport)
        api_request.set_post_method()
        api_request.set_url('device/{deviceId}/notification', deviceId=self._id)
        api_request.set_action('notification/insert')
        api_request.set('notification', notification, True)
        api_request.set_response_key('notification')
        exception_message = 'Notification send failure'
        notification = self._token.execute_authorized_request(api_request,
                                                              exception_message)
        notification[Notification.DEVICE_ID_KEY] = self._id
        notification[Notification.NOTIFICATION_KEY] = notification_name
        notification[Notification.PARAMETERS_KEY] = parameters
        return Notification(notification)
