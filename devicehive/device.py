# Copyright (C) 2018 DataArt
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================


from devicehive.api_request import AuthApiRequest
from devicehive.command import Command
from devicehive.notification import Notification
from devicehive.api_request import ApiRequestError


class Device(object):
    """Device class."""

    ID_KEY = 'id'
    NAME_KEY = 'name'
    DATA_KEY = 'data'
    NETWORK_ID_KEY = 'networkId'
    DEVICE_TYPE_ID_KEY = 'deviceTypeId'
    IS_BLOCKED_KEY = 'isBlocked'

    def __init__(self, api, device=None):
        self._api = api
        self._id = None
        self.name = None
        self.data = None
        self.network_id = None
        self.device_type_id = None
        self.is_blocked = None
        if device:
            self._init(device)

    def _init(self, device):
        self._id = device[self.ID_KEY]
        self.name = device[self.NAME_KEY]
        self.data = device[self.DATA_KEY]
        self.network_id = device[self.NETWORK_ID_KEY]
        self.device_type_id = device[self.DEVICE_TYPE_ID_KEY]
        self.is_blocked = device[self.IS_BLOCKED_KEY]

    def _ensure_exists(self):
        if self._id:
            return
        raise DeviceError('Device does not exist.')

    @property
    def id(self):
        return self._id

    def get(self, device_id):
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.url('device/{deviceId}', deviceId=device_id)
        auth_api_request.action('device/get')
        auth_api_request.response_key('device')
        device = auth_api_request.execute('Device get failure.')
        self._init(device)

    def save(self):
        self._ensure_exists()
        device = {self.NAME_KEY: self.name,
                  self.DATA_KEY: self.data,
                  self.NETWORK_ID_KEY: self.network_id,
                  self.DEVICE_TYPE_ID_KEY: self.device_type_id,
                  self.IS_BLOCKED_KEY: self.is_blocked}
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.method('PUT')
        auth_api_request.url('device/{deviceId}', deviceId=self._id)
        auth_api_request.action('device/save')
        auth_api_request.set('device', device, True)
        auth_api_request.execute('Device save failure.')

    def remove(self):
        self._ensure_exists()
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.method('DELETE')
        auth_api_request.url('device/{deviceId}', deviceId=self._id)
        auth_api_request.action('device/delete')
        auth_api_request.execute('Device remove failure.')
        self._id = None
        self.name = None
        self.data = None
        self.network_id = None
        self.device_type_id = None
        self.is_blocked = None

    def subscribe_insert_commands(self, names=(), timestamp=None):
        self._ensure_exists()
        return self._api.subscribe_insert_commands(self.id, names=names,
                                                   timestamp=timestamp)

    def subscribe_update_commands(self, names=(), timestamp=None):
        self._ensure_exists()
        return self._api.subscribe_update_commands(self.id, names=names,
                                                   timestamp=timestamp)

    def list_commands(self, start=None, end=None, command=None, status=None,
                      sort_field=None, sort_order=None, take=None, skip=None):
        self._ensure_exists()
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.url('device/{deviceId}/command', deviceId=self._id)
        auth_api_request.action('command/list')
        auth_api_request.param('start', start)
        auth_api_request.param('end', end)
        auth_api_request.param('command', command)
        auth_api_request.param('status', status)
        auth_api_request.param('sortField', sort_field)
        auth_api_request.param('sortOrder', sort_order)
        auth_api_request.param('take', take)
        auth_api_request.param('skip', skip)
        auth_api_request.response_key('commands')
        commands = auth_api_request.execute('List commands failure.')
        return [Command(self._api, command) for command in commands]

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
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.method('POST')
        auth_api_request.url('device/{deviceId}/command', deviceId=self._id)
        auth_api_request.action('command/insert')
        auth_api_request.set('command', command, True)
        auth_api_request.response_key('command')
        command = auth_api_request.execute('Command send failure.')
        command[Command.DEVICE_ID_KEY] = self._id
        command[Command.COMMAND_KEY] = command_name
        command[Command.PARAMETERS_KEY] = parameters
        command[Command.LIFETIME_KEY] = lifetime
        command[Command.STATUS_KEY] = status
        command[Command.RESULT_KEY] = result
        return Command(self._api, command)

    def subscribe_notifications(self, names=(), timestamp=None):
        self._ensure_exists()
        return self._api.subscribe_notifications(self.id, names=names,
                                                 timestamp=timestamp)

    def list_notifications(self, start=None, end=None, notification=None,
                           sort_field=None, sort_order=None, take=None,
                           skip=None):
        self._ensure_exists()
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.url('device/{deviceId}/notification',
                             deviceId=self._id)
        auth_api_request.action('notification/list')
        auth_api_request.param('start', start)
        auth_api_request.param('end', end)
        auth_api_request.param('notification', notification)
        auth_api_request.param('sortField', sort_field)
        auth_api_request.param('sortOrder', sort_order)
        auth_api_request.param('take', take)
        auth_api_request.param('skip', skip)
        auth_api_request.response_key('notifications')
        notifications = auth_api_request.execute('List notifications failure.')
        return [Notification(notification) for notification in notifications]

    def send_notification(self, notification_name, parameters=None,
                          timestamp=None):
        self._ensure_exists()
        notification = {'notification': notification_name}
        if parameters:
            notification['parameters'] = parameters
        if timestamp:
            notification['timestamp'] = timestamp
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.method('POST')
        auth_api_request.url('device/{deviceId}/notification',
                             deviceId=self._id)
        auth_api_request.action('notification/insert')
        auth_api_request.set('notification', notification, True)
        auth_api_request.response_key('notification')
        notification = auth_api_request.execute('Notification send failure.')
        notification[Notification.DEVICE_ID_KEY] = self._id
        notification[Notification.NOTIFICATION_KEY] = notification_name
        notification[Notification.PARAMETERS_KEY] = parameters
        return Notification(notification)


class DeviceError(ApiRequestError):
    """Device error."""
