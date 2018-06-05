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
        return self._api.list_commands(device_id=self._id, start=start, end=end,
                                       command=command, status=status,
                                       sort_field=sort_field,
                                       sort_order=sort_order,
                                       take=take, skip=skip)

    def send_command(self, command_name, parameters=None, lifetime=None,
                     timestamp=None, status=None, result=None):
        self._ensure_exists()
        return self._api.send_command(device_id=self._id,
                                      command_name=command_name,
                                      parameters=parameters, lifetime=lifetime,
                                      timestamp=timestamp, status=status,
                                      result=result)

    def subscribe_notifications(self, names=(), timestamp=None):
        self._ensure_exists()
        return self._api.subscribe_notifications(self.id, names=names,
                                                 timestamp=timestamp)

    def list_notifications(self, start=None, end=None, notification=None,
                           sort_field=None, sort_order=None, take=None,
                           skip=None):
        self._ensure_exists()
        return self._api.list_notifications(device_id=self._id, start=start,
                                            end=end,
                                            notification=notification,
                                            sort_field=sort_field,
                                            sort_order=sort_order,
                                            take=take, skip=skip)

    def send_notification(self, notification_name, parameters=None,
                          timestamp=None):
        self._ensure_exists()
        return self._api.send_notification(device_id=self._id,
                                           notification_name=notification_name,
                                           parameters=parameters,
                                           timestamp=timestamp)


class DeviceError(ApiRequestError):
    """Device error."""
