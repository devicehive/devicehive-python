from devicehive.token import Token
from devicehive.api_request import ApiRequest
from devicehive.api_request import AuthApiRequest
from devicehive.api_request import AuthSubscriptionApiRequest
from devicehive.device import Device
from devicehive.device import DeviceError


class Api(object):
    """Api class."""

    def __init__(self, transport, auth):
        self._transport = transport
        self._token = Token(self, auth)
        self._subscriptions = {}
        self._removed_subscription_ids = {}
        self.server_timestamp = None

    @property
    def transport(self):
        return self._transport

    @property
    def token(self):
        return self._token

    def ensure_subscription_not_exist(self, action, *device_ids):
        for device_id in device_ids:
            if not self.subscription_id(action, device_id):
                continue
            raise DeviceError('Device %s has already subscribed for %s.' %
                              (device_id, action))

    def ensure_subscription_exist(self, action, *device_ids):
        for device_id in device_ids:
            if self.subscription_id(action, device_id):
                continue
            raise DeviceError('Device %s has not subscribed for %s.' %
                              (device_id, action))

    def subscription_id(self, action, device_id):
        if not self._subscriptions.get(action):
            return None
        return self._subscriptions[action].get(device_id)

    def subscription(self, action, device_id, subscription_id):
        if not self._subscriptions.get(action):
            self._subscriptions[action] = {}
        self._subscriptions[action][device_id] = subscription_id

    def remove_subscription(self, action, subscription_id):
        subscription_ids = {}
        for device_id in self._subscriptions[action]:
            if self._subscriptions[action][device_id] == subscription_id:
                continue
            subscription_ids[device_id] = self._subscriptions[action][device_id]
        self._subscriptions[action] = subscription_ids
        if not self._removed_subscription_ids.get(action):
            self._removed_subscription_ids[action] = []
        self._removed_subscription_ids[action].append(subscription_id)

    def removed_subscription_id_exists(self, action, subscription_id):
        subscription_ids = self._removed_subscription_ids.get(action)
        if not subscription_ids:
            return False
        return subscription_id in subscription_ids

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

    def subscribe_insert_commands(self, device_ids, names=None, limit=None,
                                  timestamp=None):
        action = 'command/insert'
        join_device_ids = ','.join(device_ids)
        join_names = ','.join(names) if names else None
        if not timestamp:
            timestamp = self.server_timestamp
        auth_subscription_api_request = AuthSubscriptionApiRequest(self)
        auth_subscription_api_request.action(action)
        auth_subscription_api_request.url('device/command/poll',
                                          deviceIds=join_device_ids)
        auth_subscription_api_request.param('names', join_names)
        auth_subscription_api_request.param('limit', limit)
        auth_subscription_api_request.param('timestamp', timestamp)
        auth_subscription_api_request.response_key('command')
        api_request = ApiRequest(self)
        api_request.action('command/subscribe')
        api_request.set('deviceIds', device_ids)
        api_request.set('names', names)
        api_request.set('limit', limit)
        api_request.set('timestamp', timestamp)
        api_request.subscription_request(auth_subscription_api_request)
        subscription = api_request.execute('Subscribe insert commands failure.')
        subscription_id = subscription['subscriptionId']
        for device_id in device_ids:
            self.subscription(action, device_id, subscription_id)

    def subscribe_notifications(self, device_ids, names=None, timestamp=None):
        join_device_ids = ','.join(device_ids)
        join_names = ','.join(names) if names else None
        if not timestamp:
            timestamp = self.server_timestamp
        auth_subscription_api_request = AuthSubscriptionApiRequest(self)
        auth_subscription_api_request.action('notification/insert')
        auth_subscription_api_request.url('device/notification/poll',
                                          deviceIds=join_device_ids)
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
        return subscription['subscriptionId']

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
