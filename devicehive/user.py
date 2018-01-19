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
from devicehive.network import Network
from devicehive.device_type import DeviceType


class User(object):
    """User class."""

    ID_KEY = 'id'
    LOGIN_KEY = 'login'
    LAST_LOGIN_KEY = 'lastLogin'
    INTRO_REVIEWED_KEY = 'introReviewed'
    ROLE_KEY = 'role'
    STATUS_KEY = 'status'
    DATA_KEY = 'data'
    PASSWORD_KEY = 'password'
    NETWORKS_KEY = 'networks'
    ALL_DEVICE_TYPES_KEY = 'allDeviceTypesAvailable'
    ADMINISTRATOR_ROLE = 0
    CLIENT_ROLE = 1
    ACTIVE_STATUS = 0
    LOCKED_STATUS = 1
    DISABLED_STATUS = 2

    def __init__(self, api, user=None):
        self._api = api
        self._id = None
        self._login = None
        self._last_login = None
        self._intro_reviewed = None
        self._all_device_types_available = None
        self.role = None
        self.status = None
        self.data = None

        if user:
            self._init(user)

    def _init(self, user):
        self._id = user[self.ID_KEY]
        self._login = user[self.LOGIN_KEY]
        self._last_login = user[self.LAST_LOGIN_KEY]
        self._intro_reviewed = user[self.INTRO_REVIEWED_KEY]
        self._all_device_types_available = user[self.ALL_DEVICE_TYPES_KEY]
        self.role = user[self.ROLE_KEY]
        self.status = user[self.STATUS_KEY]
        self.data = user[self.DATA_KEY]

    def _ensure_exists(self):
        if self._id:
            return
        raise UserError('User does not exist.')

    def _ensure_all_device_types_available(self):
        if self._all_device_types_available:
            return
        raise UserError('User does not have access to all device types.')

    def _ensure_not_all_device_types_available(self):
        if not self._all_device_types_available:
            return
        raise UserError('User have access to all device types.')

    @property
    def id(self):
        return self._id

    @property
    def login(self):
        return self._login

    @property
    def last_login(self):
        return self._last_login

    @property
    def intro_reviewed(self):
        return self._intro_reviewed

    @property
    def all_device_types_available(self):
        return self._all_device_types_available

    def get_current(self):
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.url('user/current')
        auth_api_request.action('user/getCurrent')
        auth_api_request.response_key('current')
        user = auth_api_request.execute('Current user get failure.')
        self._init(user)

    def get(self, user_id):
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.url('user/{userId}', userId=user_id)
        auth_api_request.action('user/get')
        auth_api_request.response_key('user')
        user = auth_api_request.execute('User get failure.')
        self._init(user)

    def save(self):
        self._ensure_exists()
        user = {self.ROLE_KEY: self.role,
                self.STATUS_KEY: self.status,
                self.DATA_KEY: self.data}
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.method('PUT')
        auth_api_request.url('user/{userId}', userId=self._id)
        auth_api_request.action('user/update')
        auth_api_request.set('user', user, True)
        auth_api_request.execute('User save failure.')

    def update_password(self, password):
        self._ensure_exists()
        user = {self.PASSWORD_KEY: password}
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.method('PUT')
        auth_api_request.url('user/{userId}', userId=self._id)
        auth_api_request.action('user/update')
        auth_api_request.set('user', user, True)
        auth_api_request.execute('User password update failure.')

    def remove(self):
        self._ensure_exists()
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.method('DELETE')
        auth_api_request.url('user/{userId}', userId=self._id)
        auth_api_request.action('user/delete')
        auth_api_request.execute('User remove failure.')
        self._id = None
        self._login = None
        self._last_login = None
        self._intro_reviewed = None
        self._all_device_types_available = None
        self.role = None
        self.status = None
        self.data = None

    def list_networks(self):
        self._ensure_exists()
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.url('user/{userId}', userId=self._id)
        auth_api_request.action('user/get')
        auth_api_request.response_key('user')
        user = auth_api_request.execute('List networks failure.')
        return [Network(self._api, network)
                for network in user[User.NETWORKS_KEY]]

    def assign_network(self, network_id):
        self._ensure_exists()
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.method('PUT')
        auth_api_request.url('user/{userId}/network/{networkId}',
                             userId=self._id, networkId=network_id)
        auth_api_request.action('user/assignNetwork')
        auth_api_request.execute('Assign network failure.')

    def unassign_network(self, network_id):
        self._ensure_exists()
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.method('DELETE')
        auth_api_request.url('user/{userId}/network/{networkId}',
                             userId=self._id, networkId=network_id)
        auth_api_request.action('user/unassignNetwork')
        auth_api_request.execute('Unassign network failure.')

    def list_device_types(self):
        self._ensure_exists()
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.url('user/{userId}/devicetype', userId=self._id)
        auth_api_request.action('user/getDeviceTypes')
        auth_api_request.response_key('deviceTypes')
        device_types = auth_api_request.execute('List device types failure.')
        return [DeviceType(self._api, device_type)
                for device_type in device_types]

    def allow_all_device_types(self):
        self._ensure_exists()
        self._ensure_not_all_device_types_available()
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.method('PUT')
        auth_api_request.url('user/{userId}/devicetype/all', userId=self._id)
        auth_api_request.action('user/allowAllDeviceTypes')
        auth_api_request.execute('Assign all device types failure.')
        self._all_device_types_available = True

    def disallow_all_device_types(self):
        self._ensure_exists()
        self._ensure_all_device_types_available()
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.method('DELETE')
        auth_api_request.url('user/{userId}/devicetype/all', userId=self._id)
        auth_api_request.action('user/disallowAllDeviceTypes')
        auth_api_request.execute('Unassign device type failure.')
        self._all_device_types_available = False

    def assign_device_type(self, device_type_id):
        self._ensure_exists()
        self._ensure_not_all_device_types_available()
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.method('PUT')
        auth_api_request.url('user/{userId}/devicetype/{deviceTypeId}',
                             userId=self._id, deviceTypeId=device_type_id)
        auth_api_request.action('user/assignDeviceType')
        auth_api_request.execute('Assign device type failure.')

    def unassign_device_type(self, device_type_id):
        self._ensure_exists()
        self._ensure_not_all_device_types_available()
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.method('DELETE')
        auth_api_request.url('user/{userId}/devicetype/{deviceTypeId}',
                             userId=self._id, deviceTypeId=device_type_id)
        auth_api_request.action('user/unassignDeviceType')
        auth_api_request.execute('Unassign device type failure.')


class UserError(ApiRequestError):
    """User error."""
