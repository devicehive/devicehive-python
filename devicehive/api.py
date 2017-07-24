from devicehive.api_request import ApiRequest
from devicehive.token import Token
from devicehive.device import Device


class Api(object):
    """Api class."""

    def __init__(self, transport, authentication):
        self._transport = transport
        self._token = Token(transport, authentication)

    def authenticate(self):
        self._token.authenticate()

    def get_info(self):
        api_request = ApiRequest(self._transport)
        api_request.url('info')
        api_request.action('server/info')
        api_request.response_key('info')
        exception_message = 'Info get failure'
        info = api_request.execute(exception_message)
        return {'api_version': info['apiVersion'],
                'server_timestamp': info['serverTimestamp'],
                'rest_server_url': info.get('restServerUrl'),
                'websocket_server_url': info.get('webSocketServerUrl')}

    def get_cluster_info(self):
        api_request = ApiRequest(self._transport)
        api_request.url('info/config/cluster')
        api_request.action('cluster/info')
        api_request.response_key('clusterInfo')
        exception_message = 'Cluster info get failure'
        return api_request.execute(exception_message)

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
        api_request = ApiRequest(self._transport)
        api_request.method('POST')
        api_request.url('token/create')
        api_request.action('token/create')
        api_request.set('payload', payload, True)
        exception_message = 'Token refresh failure'
        tokens = self._token.execute_authorized_request(api_request,
                                                        exception_message)
        return {'refresh_token': tokens['refreshToken'],
                'access_token': tokens['accessToken']}

    def refresh_token(self):
        self._token.refresh()
        return self._token.access_token()

    def list_devices(self, name=None, name_pattern=None, network_id=None,
                     network_name=None, sort_field=None, sort_order=None,
                     take=None, skip=None):
        api_request = ApiRequest(self._transport)
        api_request.url('device')
        api_request.action('device/list')
        api_request.param('name', name)
        api_request.param('namePattern', name_pattern)
        api_request.param('networkId', network_id)
        api_request.param('networkName', network_name)
        api_request.param('sortField', sort_field)
        api_request.param('sortOrder', sort_order)
        api_request.param('take', take)
        api_request.param('skip', skip)
        api_request.response_key('devices')
        exception_message = 'List devices failure'
        devices = self._token.execute_authorized_request(api_request,
                                                         exception_message)
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
