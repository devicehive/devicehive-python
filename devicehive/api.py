from devicehive.api_request import ApiRequest
from devicehive.info import Info
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
        api_request.set_url('info')
        api_request.set_action('server/info')
        response_key = 'info'
        api_request.set_response_key(response_key)
        response = api_request.execute('Info get failure')
        info = response.value(response_key)
        return {'api_version': info['apiVersion'],
                'server_timestamp': info['serverTimestamp'],
                'rest_server_url': info.get('restServerUrl'),
                'websocket_server_url': info.get('webSocketServerUrl')}

    def get_cluster_info(self):
        info = Info(self._transport)
        return info.get_cluster()

    def create_token(self, user_id, **payload):
        return self._token.create(user_id, **payload)

    def refresh_token(self):
        self._token.refresh()
        return self._token.access_token()

    def list_devices(self, name=None, name_pattern=None, network_id=None,
                     network_name=None, sort_field=None, sort_order=None,
                     take=None, skip=None):
        api_request = ApiRequest(self._transport)
        api_request.set_url('device')
        api_request.set_action('device/list')
        api_request.set_param('name', name)
        api_request.set_param('namePattern', name_pattern)
        api_request.set_param('networkId', network_id)
        api_request.set_param('networkName', network_name)
        api_request.set_param('sortField', sort_field)
        api_request.set_param('sortOrder', sort_order)
        api_request.set_param('take', take)
        api_request.set_param('skip', skip)
        response_key = 'devices'
        api_request.set_response_key(response_key)
        exception_message = 'List devices failure'
        response = self._token.execute_authorized_request(api_request,
                                                          exception_message)
        devices = response.value(response_key)
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
        if not self._transport.connected():
            return
        self._transport.disconnect()
