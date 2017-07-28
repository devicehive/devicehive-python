from devicehive.api_request import ApiRequest
from devicehive.api_request import AuthApiRequest
from devicehive.device import Device


class Api(object):
    """Api class."""

    def __init__(self, transport, token):
        self._transport = transport
        self._token = token
        self.server_timestamp = None

    def get_info(self):
        api_request = ApiRequest(self._transport)
        api_request.url('info')
        api_request.action('server/info')
        api_request.response_key('info')
        info = api_request.execute('Info get failure')
        return {'api_version': info['apiVersion'],
                'server_timestamp': info['serverTimestamp'],
                'rest_server_url': info.get('restServerUrl'),
                'websocket_server_url': info.get('webSocketServerUrl')}

    def get_cluster_info(self):
        api_request = ApiRequest(self._transport)
        api_request.url('info/config/cluster')
        api_request.action('cluster/info')
        api_request.response_key('clusterInfo')
        return api_request.execute('Cluster info get failure')

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
        auth_api_request = AuthApiRequest(self._transport, self._token)
        auth_api_request.method('POST')
        auth_api_request.url('token/create')
        auth_api_request.action('token/create')
        auth_api_request.set('payload', payload, True)
        tokens = auth_api_request.execute('Token refresh failure')
        return {'refresh_token': tokens['refreshToken'],
                'access_token': tokens['accessToken']}

    def refresh_token(self):
        self._token.refresh()
        return self._token.access_token

    def list_devices(self, name=None, name_pattern=None, network_id=None,
                     network_name=None, sort_field=None, sort_order=None,
                     take=None, skip=None):
        auth_api_request = AuthApiRequest(self._transport, self._token)
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
        devices = auth_api_request.execute('List devices failure')
        return [Device(self._transport, self._token, device)
                for device in devices]

    def get_device(self, device_id):
        device = Device(self._transport, self._token)
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
        device = Device(self._transport, self._token, device)
        device.save()
        device.get(device_id)
        return device

    def disconnect(self):
        if not self._transport.connected:
            return
        self._transport.disconnect()
