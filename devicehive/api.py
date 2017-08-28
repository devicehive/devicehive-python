from devicehive.token import Token
from devicehive.api_request import ApiRequest
from devicehive.api_request import AuthApiRequest
from devicehive.api_request import AuthSubscriptionApiRequest
from devicehive.api_request import RemoveSubscriptionApiRequest
from devicehive.device import Device
from devicehive.device import DeviceError
from devicehive.network import Network
from devicehive.user import User


class Api(object):
    """Api class."""

    def __init__(self, transport, auth):
        self._transport = transport
        self._token = Token(self, auth)
        self._connected = True
        self._subscriptions = {}
        self._removed_subscription_ids = {}
        self.server_timestamp = None

    def _unsubscribe(self, action, device_ids):
        subscription_ids, subscriptions, subscription_calls = [], [], []
        for device_id in device_ids:
            subscription_id = self.subscription_id(action, device_id)
            if subscription_id in subscription_ids:
                continue
            subscription_ids.append(subscription_id)
        for subscription in self._subscriptions[action]:
            if subscription['device_id'] in device_ids:
                continue
            if subscription['subscription_id'] in subscription_ids:
                subscriptions.append(subscription)
        for subscription in subscriptions:
            found = False
            for subscription_call in subscription_calls:
                if subscription_call['names'] == subscription['names']:
                    found = True
                    device_id = subscription['device_id']
                    subscription_call['device_ids'].append(device_id)
                    break
            if not found:
                subscription_call = {'device_ids': [subscription['device_id']],
                                     'names': subscription['names']}
                subscription_calls.append(subscription_call)
        return subscription_ids, subscription_calls

    @property
    def transport(self):
        return self._transport

    @property
    def token(self):
        return self._token

    @property
    def connected(self):
        return self._connected

    def ensure_subscription_not_exist(self, action, device_ids):
        for device_id in device_ids:
            if not self.subscription_id(action, device_id):
                continue
            raise DeviceError('Device %s has already subscribed for %s.' %
                              (device_id, action))

    def ensure_subscription_exists(self, action, device_ids):
        for device_id in device_ids:
            if self.subscription_id(action, device_id):
                continue
            raise DeviceError('Device %s has not subscribed for %s.' %
                              (device_id, action))

    def subscription_id(self, action, device_id):
        if not self._subscriptions.get(action):
            return None
        for subscription in self._subscriptions[action]:
            if subscription['device_id'] != device_id:
                continue
            return subscription['subscription_id']

    def subscription(self, action, subscription_id, device_ids, names):
        if not self._subscriptions.get(action):
            self._subscriptions[action] = []
        subscriptions = [{'subscription_id': subscription_id,
                          'device_id': device_id,
                          'names': names}
                         for device_id in device_ids]
        self._subscriptions[action].extend(subscriptions)

    def remove_subscription(self, action, subscription_id):
        subscriptions = [subscription
                         for subscription in self._subscriptions[action]
                         if subscription['subscription_id'] != subscription_id]
        self._subscriptions[action] = subscriptions
        if not self._removed_subscription_ids.get(action):
            self._removed_subscription_ids[action] = []
        self._removed_subscription_ids[action].append(subscription_id)

    def removed_subscription_id_exists(self, action, subscription_id):
        subscription_ids = self._removed_subscription_ids.get(action)
        if not subscription_ids:
            return False
        return subscription_id in subscription_ids

    def resubscribe(self):
        subscription_calls = {}
        for action in self._subscriptions:
            subscription_calls[action] = []
            for subscription in self._subscriptions[action]:
                found = False
                for subscription_call in subscription_calls[action]:
                    if subscription_call['names'] == subscription['names']:
                        found = True
                        device_id = subscription['device_id']
                        subscription_call['device_ids'].append(device_id)
                        break
                if not found:
                    device_id = subscription['device_id']
                    subscription_call = {'device_ids': [device_id],
                                         'names': subscription['names']}
                    subscription_calls[action].append(subscription_call)
        self._subscriptions = {}
        action = 'command/insert'
        if action in subscription_calls:
            for subscription_call in subscription_calls[action]:
                self.subscribe_insert_commands(**subscription_call)
        action = 'command/update'
        if action in subscription_calls:
            for subscription_call in subscription_calls[action]:
                self.subscribe_update_commands(**subscription_call)
        action = 'notification/insert'
        if action in subscription_calls:
            for subscription_call in subscription_calls[action]:
                self.subscribe_notifications(**subscription_call)

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
                     network_ids=None, device_ids=None):
        payload = {'userId': user_id}
        if expiration:
            payload['expiration'] = expiration
        if actions:
            payload['actions'] = actions
        if network_ids:
            payload['networkIds'] = network_ids
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

    def subscribe_insert_commands(self, device_ids, names=None, timestamp=None):
        action = 'command/insert'
        self.ensure_subscription_not_exist(action, device_ids)
        join_device_ids = ','.join(device_ids)
        join_names = ','.join(names) if names else None
        if not timestamp:
            timestamp = self.server_timestamp
        auth_subscription_api_request = AuthSubscriptionApiRequest(self)
        auth_subscription_api_request.action(action)
        auth_subscription_api_request.url('device/command/poll')
        auth_subscription_api_request.param('deviceIds', join_device_ids)
        auth_subscription_api_request.param('names', join_names)
        auth_subscription_api_request.param('timestamp', timestamp)
        auth_subscription_api_request.response_key('command')
        api_request = ApiRequest(self)
        api_request.action('command/subscribe')
        api_request.set('deviceIds', device_ids)
        api_request.set('names', names)
        api_request.set('timestamp', timestamp)
        api_request.subscription_request(auth_subscription_api_request)
        subscription = api_request.execute('Subscribe insert commands failure.')
        subscription_id = subscription['subscriptionId']
        self.subscription(action, subscription_id, device_ids, names)

    def unsubscribe_insert_commands(self, device_ids):
        action = 'command/insert'
        self.ensure_subscription_exists(action, device_ids)
        subscription_ids, subscription_calls = self._unsubscribe(action,
                                                                 device_ids)
        for subscription_id in subscription_ids:
            remove_subscription_api_request = RemoveSubscriptionApiRequest()
            remove_subscription_api_request.subscription_id(subscription_id)
            api_request = ApiRequest(self)
            api_request.action('command/unsubscribe')
            api_request.set('subscriptionId', subscription_id)
            api_request.remove_subscription_request(
                remove_subscription_api_request)
            api_request.execute('Unsubscribe insert commands failure.')
            self.remove_subscription(action, subscription_id)
        timestamp = self.get_info()['server_timestamp']
        for subscription_call in subscription_calls:
            subscription_call['timestamp'] = timestamp
            self.subscribe_insert_commands(**subscription_call)

    def subscribe_update_commands(self, device_ids, names=None, timestamp=None):
        action = 'command/update'
        self.ensure_subscription_not_exist(action, device_ids)
        join_device_ids = ','.join(device_ids)
        join_names = ','.join(names) if names else None
        if not timestamp:
            timestamp = self.server_timestamp
        auth_subscription_api_request = AuthSubscriptionApiRequest(self)
        auth_subscription_api_request.action(action)
        auth_subscription_api_request.url('device/command/poll')
        auth_subscription_api_request.param('returnUpdatedCommands', True)
        auth_subscription_api_request.param('deviceIds', join_device_ids)
        auth_subscription_api_request.param('names', join_names)
        auth_subscription_api_request.param('timestamp', timestamp)
        auth_subscription_api_request.response_timestamp_key('lastUpdated')
        auth_subscription_api_request.response_key('command')
        api_request = ApiRequest(self)
        api_request.action('command/subscribe')
        api_request.set('returnUpdatedCommands', True)
        api_request.set('deviceIds', device_ids)
        api_request.set('names', names)
        api_request.set('timestamp', timestamp)
        api_request.subscription_request(auth_subscription_api_request)
        subscription = api_request.execute('Subscribe update commands failure.')
        subscription_id = subscription['subscriptionId']
        self.subscription(action, subscription_id, device_ids, names)

    def unsubscribe_update_commands(self, device_ids):
        action = 'command/update'
        self.ensure_subscription_exists(action, device_ids)
        subscription_ids, subscription_calls = self._unsubscribe(action,
                                                                 device_ids)
        for subscription_id in subscription_ids:
            remove_subscription_api_request = RemoveSubscriptionApiRequest()
            remove_subscription_api_request.subscription_id(subscription_id)
            api_request = ApiRequest(self)
            api_request.action('command/unsubscribe')
            api_request.set('subscriptionId', subscription_id)
            api_request.remove_subscription_request(
                remove_subscription_api_request)
            api_request.execute('Unsubscribe update commands failure.')
            self.remove_subscription(action, subscription_id)
        timestamp = self.get_info()['server_timestamp']
        for subscription_call in subscription_calls:
            subscription_call['timestamp'] = timestamp
            self.subscribe_update_commands(**subscription_call)

    def subscribe_notifications(self, device_ids, names=None, timestamp=None):
        action = 'notification/insert'
        self.ensure_subscription_not_exist(action, device_ids)
        join_device_ids = ','.join(device_ids)
        join_names = ','.join(names) if names else None
        if not timestamp:
            timestamp = self.server_timestamp
        auth_subscription_api_request = AuthSubscriptionApiRequest(self)
        auth_subscription_api_request.action(action)
        auth_subscription_api_request.url('device/notification/poll')
        auth_subscription_api_request.param('deviceIds', join_device_ids)
        auth_subscription_api_request.param('names', join_names)
        auth_subscription_api_request.param('timestamp', timestamp)
        auth_subscription_api_request.response_key('notification')
        api_request = ApiRequest(self)
        api_request.action('notification/subscribe')
        api_request.set('deviceIds', device_ids)
        api_request.set('names', names)
        api_request.set('timestamp', timestamp)
        api_request.subscription_request(auth_subscription_api_request)
        subscription = api_request.execute('Subscribe notifications failure.')
        subscription_id = subscription['subscriptionId']
        self.subscription(action, subscription_id, device_ids, names)

    def unsubscribe_notifications(self, device_ids):
        action = 'notification/insert'
        self.ensure_subscription_exists(action, device_ids)
        subscription_ids, subscription_calls = self._unsubscribe(action,
                                                                 device_ids)
        for subscription_id in subscription_ids:
            remove_subscription_api_request = RemoveSubscriptionApiRequest()
            remove_subscription_api_request.subscription_id(subscription_id)
            api_request = ApiRequest(self)
            api_request.action('notification/unsubscribe')
            api_request.set('subscriptionId', subscription_id)
            api_request.remove_subscription_request(
                remove_subscription_api_request)
            api_request.execute('Unsubscribe notifications failure.')
            self.remove_subscription(action, subscription_id)
        timestamp = self.get_info()['server_timestamp']
        for subscription_call in subscription_calls:
            subscription_call['timestamp'] = timestamp
            self.subscribe_notifications(**subscription_call)

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
                   is_blocked=False):
        if not name:
            name = device_id
        device = {Device.ID_KEY: device_id,
                  Device.NAME_KEY: name,
                  Device.DATA_KEY: data,
                  Device.NETWORK_ID_KEY: network_id,
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

    def create_user(self, login, password, role, data):
        status = User.ACTIVE_STATUS
        user = {User.LOGIN_KEY: login,
                User.ROLE_KEY: role,
                User.STATUS_KEY: status,
                User.DATA_KEY: data,
                User.PASSWORD_KEY: password}
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
