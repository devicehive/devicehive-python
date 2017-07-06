from devicehive.api_unit import Info
from devicehive.api_unit import Token
from devicehive.api_unit import Device


class Api(object):
    """Api class."""

    def __init__(self, transport, authentication):
        self._transport = transport
        self._token = Token(transport, authentication)

    def authenticate(self):
        self._token.authenticate()

    def get_info(self):
        info = Info(self._transport)
        return info.get()

    def get_cluster_info(self):
        info = Info(self._transport)
        return info.get_cluster_info()

    def create_token(self, user_id, expiration=None, actions=None,
                     network_ids=None, device_ids=None):
        return self._token.create(user_id, expiration, actions, network_ids,
                                  device_ids)

    def refresh_token(self):
        self._token.refresh()
        return self._token.access_token()

    def list_devices(self, name=None, name_pattern=None, network_id=None,
                     network_name=None, sort_field=None, sort_order=None,
                     take=None, skip=None):
        # TODO: implement filters for websocket when API will be extended.
        url = 'device'
        action = 'device/list'
        request = {}
        params = {'data_key': 'devices', 'params': {}}
        if name:
            params['params']['name'] = name
        if name_pattern:
            params['params']['namePattern'] = name_pattern
        if network_id:
            params['params']['networkId'] = network_id
        if network_name:
            params['params']['networkName'] = network_name
        if sort_field:
            params['params']['sortField'] = sort_field
        if sort_order:
            params['params']['sortOrder'] = sort_order
        if take:
            params['params']['take'] = take
        if skip:
            params['params']['skip'] = skip
        response = self._token.authorized_request(url, action, request,
                                                  **params)
        assert response.is_success, 'List devices failure'
        devices = []
        for device in response.data['devices']:
            devices.append(Device(self._transport, self._token, device['id'],
                                  device['name'], device['data'],
                                  device['networkId'], device['isBlocked']))
        return devices

    def get_device(self, device_id):
        device = Device(self._transport, self._token)
        device.get(device_id)
        if device.id:
            return device
