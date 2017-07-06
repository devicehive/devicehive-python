from devicehive.api_unit import Info
from devicehive.api_unit import Token
from devicehive.api_unit import Configuration
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

    def list_devices(self, **filters):
        device = Device(self._transport, self._token)
        return device.list(**filters)

    def get_device(self, device_id):
        device = Device(self._transport, self._token)
        device.get(device_id)
        if device.id:
            return device
