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


from devicehive.token import Token
from devicehive.api_request import ApiRequest
from devicehive.api_request import AuthApiRequest
from devicehive.api_request import AuthSubscriptionApiRequest
from devicehive.device import Device
from devicehive.subscription import CommandsSubscription, \
    NotificationsSubscription
from devicehive.network import Network
from devicehive.device_type import DeviceType
from devicehive.user import User


class Api(object):
    """Api class."""

    def __init__(self, transport, auth):
        self._transport = transport
        self._token = Token(self, auth)
        self._connected = True
        self.server_timestamp = None

    @property
    def transport(self):
        return self._transport

    @property
    def token(self):
        return self._token

    @property
    def connected(self):
        return self._connected

    def get_info(self):
        api_request = ApiRequest(self)
        api_request.url('info')
        api_request.action('server/info')
        api_request.response_key('info')
        info = api_request.execute('Info get failure.')
        return {'api_version': info['apiVersion'],
                'server_timestamp': info['serverTimestamp'],
                'rest_server_url': info.get('restServerUrl'),
                'websocket_server_url': info.get('webSocketServerUrl')}

    def get_cluster_info(self):
        api_request = ApiRequest(self)
        api_request.url('info/config/cluster')
        api_request.action('cluster/info')
        api_request.response_key('clusterInfo')
        return api_request.execute('Cluster info get failure.')

    def get_property(self, name):
        auth_api_request = AuthApiRequest(self)
        auth_api_request.url('configuration/{name}', name=name)
        auth_api_request.action('configuration/get')
        auth_api_request.response_key('configuration')
        configuration = auth_api_request.execute('Get property failure.')
        return {'entity_version': configuration['entityVersion'],
                'name': configuration['name'],
                'value': configuration['value']}

    def set_property(self, name, value):
        auth_api_request = AuthApiRequest(self)
        auth_api_request.method('PUT')
        auth_api_request.url('configuration/{name}', name=name)
        auth_api_request.action('configuration/put')
        auth_api_request.set('value', value)
        auth_api_request.response_key('configuration')
        configuration = auth_api_request.execute('Set property failure.')
        return {'entity_version': configuration['entityVersion']}

    def delete_property(self, name):
        auth_api_request = AuthApiRequest(self)
        auth_api_request.method('DELETE')
        auth_api_request.url('configuration/{name}', name=name)
        auth_api_request.action('configuration/delete')
        auth_api_request.execute('Delete property failure.')

    def create_token(self, user_id, expiration=None, actions=None,
                     network_ids=None, device_type_ids=None, device_ids=None):
        payload = {'userId': user_id}
        if expiration:
            payload['expiration'] = expiration
        if actions:
            payload['actions'] = actions
        if network_ids:
            payload['networkIds'] = network_ids
        if device_type_ids:
            payload['deviceTypeIds'] = device_type_ids
        if device_ids:
            payload['deviceIds'] = device_ids
        auth_api_request = AuthApiRequest(self)
        auth_api_request.method('POST')
        auth_api_request.url('token/create')
        auth_api_request.action('token/create')
        auth_api_request.set('payload', payload, True)
        tokens = auth_api_request.execute('Token refresh failure.')
        return {'refresh_token': tokens['refreshToken'],
                'access_token': tokens['accessToken']}

    def refresh_token(self):
        self._token.refresh()
        return self._token.access_token

    def subscribe_insert_commands(self, device_id=None, network_ids=(),
                                  device_type_ids=(), names=(),
                                  timestamp=None):
        action = 'command/insert'
        join_names = ','.join(map(str, names))
        join_network_ids = ','.join(map(str, network_ids))
        join_device_type_ids = ','.join(map(str, device_type_ids))
        if not timestamp:
            timestamp = self.server_timestamp
        auth_subscription_api_request = AuthSubscriptionApiRequest(self)
        auth_subscription_api_request.action(action)
        auth_subscription_api_request.url('device/command/poll')
        auth_subscription_api_request.param('deviceId', device_id)
        auth_subscription_api_request.param('networkIds', join_network_ids)
        auth_subscription_api_request.param('deviceTypeIds',
                                            join_device_type_ids)
        auth_subscription_api_request.param('names', join_names)
        auth_subscription_api_request.param('timestamp', timestamp)
        auth_subscription_api_request.response_key('command')
        api_request = ApiRequest(self)
        api_request.action('command/subscribe')
        api_request.set('deviceId', device_id)
        api_request.set('networkIds', network_ids)
        api_request.set('deviceTypeIds', device_type_ids)
        api_request.set('names', names)
        api_request.set('timestamp', timestamp)
        api_request.subscription_request(auth_subscription_api_request)
        subscription = api_request.execute('Subscribe insert commands failure.')
        return CommandsSubscription(self, subscription)

    def subscribe_update_commands(self, device_id=None, network_ids=(),
                                  device_type_ids=(), names=(),
                                  timestamp=None):
        action = 'command/update'
        join_names = ','.join(map(str, names))
        join_network_ids = ','.join(map(str, network_ids))
        join_device_type_ids = ','.join(map(str, device_type_ids))
        if not timestamp:
            timestamp = self.server_timestamp
        auth_subscription_api_request = AuthSubscriptionApiRequest(self)
        auth_subscription_api_request.action(action)
        auth_subscription_api_request.url('device/command/poll')
        auth_subscription_api_request.param('returnUpdatedCommands', True)
        auth_subscription_api_request.param('deviceId', device_id)
        auth_subscription_api_request.param('networkIds', join_network_ids)
        auth_subscription_api_request.param('deviceTypeIds',
                                            join_device_type_ids)
        auth_subscription_api_request.param('names', join_names)
        auth_subscription_api_request.param('timestamp', timestamp)
        auth_subscription_api_request.response_timestamp_key('lastUpdated')
        auth_subscription_api_request.response_key('command')
        api_request = ApiRequest(self)
        api_request.action('command/subscribe')
        api_request.set('returnUpdatedCommands', True)
        api_request.set('deviceId', device_id)
        api_request.set('networkIds', network_ids)
        api_request.set('deviceTypeIds', device_type_ids)
        api_request.set('names', names)
        api_request.set('timestamp', timestamp)
        api_request.subscription_request(auth_subscription_api_request)
        subscription = api_request.execute('Subscribe update commands failure.')
        return CommandsSubscription(self, subscription)

    def subscribe_notifications(self, device_id=None, network_ids=(),
                                device_type_ids=(), names=(),
                                timestamp=None):
        action = 'notification/insert'
        join_names = ','.join(map(str, names))
        join_network_ids = ','.join(map(str, network_ids))
        join_device_type_ids = ','.join(map(str, device_type_ids))
        if not timestamp:
            timestamp = self.server_timestamp
        auth_subscription_api_request = AuthSubscriptionApiRequest(self)
        auth_subscription_api_request.action(action)
        auth_subscription_api_request.url('device/notification/poll')
        auth_subscription_api_request.param('deviceId', device_id)
        auth_subscription_api_request.param('networkIds', join_network_ids)
        auth_subscription_api_request.param('deviceTypeIds',
                                            join_device_type_ids)
        auth_subscription_api_request.param('names', join_names)
        auth_subscription_api_request.param('timestamp', timestamp)
        auth_subscription_api_request.response_key('notification')
        api_request = ApiRequest(self)
        api_request.action('notification/subscribe')
        api_request.set('deviceId', device_id)
        api_request.set('networkIds', network_ids)
        api_request.set('deviceTypeIds', device_type_ids)
        api_request.set('names', names)
        api_request.set('timestamp', timestamp)
        api_request.subscription_request(auth_subscription_api_request)
        subscription = api_request.execute('Subscribe notifications failure.')
        return NotificationsSubscription(self, subscription)

    def list_devices(self, name=None, name_pattern=None, network_id=None,
                     network_name=None, sort_field=None, sort_order=None,
                     take=None, skip=None):
        auth_api_request = AuthApiRequest(self)
        auth_api_request.url('device')
        auth_api_request.action('device/list')
        auth_api_request.param('name', name)
        auth_api_request.param('namePattern', name_pattern)
        auth_api_request.param('networkId', network_id)
        auth_api_request.param('networkName', network_name)
        auth_api_request.param('sortField', sort_field)
        auth_api_request.param('sortOrder', sort_order)
        auth_api_request.param('take', take)
        auth_api_request.param('skip', skip)
        auth_api_request.response_key('devices')
        devices = auth_api_request.execute('List devices failure.')
        return [Device(self, device) for device in devices]

    def get_device(self, device_id):
        device = Device(self)
        device.get(device_id)
        return device

    def put_device(self, device_id, name=None, data=None, network_id=None,
                   device_type_id=None, is_blocked=False):
        if not name:
            name = device_id
        device = {Device.ID_KEY: device_id,
                  Device.NAME_KEY: name,
                  Device.DATA_KEY: data,
                  Device.NETWORK_ID_KEY: network_id,
                  Device.DEVICE_TYPE_ID_KEY: device_type_id,
                  Device.IS_BLOCKED_KEY: is_blocked}
        device = Device(self, device)
        device.save()
        device.get(device_id)
        return device

    def list_networks(self, name=None, name_pattern=None, sort_field=None,
                      sort_order=None, take=None, skip=None):
        auth_api_request = AuthApiRequest(self)
        auth_api_request.url('network')
        auth_api_request.action('network/list')
        auth_api_request.param('name', name)
        auth_api_request.param('namePattern', name_pattern)
        auth_api_request.param('sortField', sort_field)
        auth_api_request.param('sortOrder', sort_order)
        auth_api_request.param('take', take)
        auth_api_request.param('skip', skip)
        auth_api_request.response_key('networks')
        networks = auth_api_request.execute('List networks failure.')
        return [Network(self, network) for network in networks]

    def get_network(self, network_id):
        network = Network(self)
        network.get(network_id)
        return network

    def create_network(self, name, description):
        network = {Network.NAME_KEY: name, Network.DESCRIPTION_KEY: description}
        auth_api_request = AuthApiRequest(self)
        auth_api_request.method('POST')
        auth_api_request.url('network')
        auth_api_request.action('network/insert')
        auth_api_request.set('network', network, True)
        auth_api_request.response_key('network')
        network = auth_api_request.execute('Network create failure.')
        network[Network.NAME_KEY] = name
        network[Network.DESCRIPTION_KEY] = description
        return Network(self, network)

    def list_device_types(self, name=None, name_pattern=None, sort_field=None,
                          sort_order=None, take=None, skip=None):
        auth_api_request = AuthApiRequest(self)
        auth_api_request.url('devicetype')
        auth_api_request.action('devicetype/list')
        auth_api_request.param('name', name)
        auth_api_request.param('namePattern', name_pattern)
        auth_api_request.param('sortField', sort_field)
        auth_api_request.param('sortOrder', sort_order)
        auth_api_request.param('take', take)
        auth_api_request.param('skip', skip)
        auth_api_request.response_key('deviceTypes')
        device_types = auth_api_request.execute('List device types failure.')
        return [DeviceType(self, device_type) for device_type in device_types]

    def get_device_type(self, device_type_id):
        device_type = DeviceType(self)
        device_type.get(device_type_id)
        return device_type

    def create_device_type(self, name, description):
        device_type = {DeviceType.NAME_KEY: name,
                       DeviceType.DESCRIPTION_KEY: description}
        auth_api_request = AuthApiRequest(self)
        auth_api_request.method('POST')
        auth_api_request.url('devicetype')
        auth_api_request.action('devicetype/insert')
        auth_api_request.set('deviceType', device_type, True)
        auth_api_request.response_key('deviceType')
        device_type = auth_api_request.execute('Device type create failure.')
        device_type[DeviceType.NAME_KEY] = name
        device_type[DeviceType.DESCRIPTION_KEY] = description
        return DeviceType(self, device_type)

    def list_users(self, login=None, login_pattern=None, role=None, status=None,
                   sort_field=None, sort_order=None, take=None, skip=None):
        auth_api_request = AuthApiRequest(self)
        auth_api_request.url('user')
        auth_api_request.action('user/list')
        auth_api_request.param('login', login)
        auth_api_request.param('loginPattern', login_pattern)
        auth_api_request.param('role', role)
        auth_api_request.param('status', status)
        auth_api_request.param('sortField', sort_field)
        auth_api_request.param('sortOrder', sort_order)
        auth_api_request.param('take', take)
        auth_api_request.param('skip', skip)
        auth_api_request.response_key('users')
        users = auth_api_request.execute('List users failure.')
        return [User(self, user) for user in users]

    def get_current_user(self):
        user = User(self)
        user.get_current()
        return user

    def get_user(self, user_id):
        user = User(self)
        user.get(user_id)
        return user

    def create_user(self, login, password, role, data,
                    all_device_types_available=True):
        status = User.ACTIVE_STATUS
        user = {User.LOGIN_KEY: login,
                User.ROLE_KEY: role,
                User.STATUS_KEY: status,
                User.DATA_KEY: data,
                User.PASSWORD_KEY: password,
                User.ALL_DEVICE_TYPES_KEY: all_device_types_available}
        auth_api_request = AuthApiRequest(self)
        auth_api_request.method('POST')
        auth_api_request.url('user')
        auth_api_request.action('user/insert')
        auth_api_request.set('user', user, True)
        auth_api_request.response_key('user')
        user = auth_api_request.execute('User create failure.')
        user[User.LOGIN_KEY] = login
        user[User.ROLE_KEY] = role
        user[User.STATUS_KEY] = status
        user[User.DATA_KEY] = data
        return User(self, user)

    def disconnect(self):
        self._connected = False
        if not self._transport.connected:
            return
        self._transport.disconnect()
