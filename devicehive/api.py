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
        # TODO: implement params for websocket when API will be extended.
        url = 'device'
        action = 'device/list'
        request = {}
        params = {'response_key': 'devices', 'params': {}}
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
        # TODO: replace assert with exception.
        assert response.success(), 'List devices failure'
        devices = response.response('devices')
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
        return device
