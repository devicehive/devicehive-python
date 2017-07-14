from devicehive.info import Info
from devicehive.token import Token
from devicehive.devices import Devices
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
        return info.get_cluster()

    def create_token(self, user_id, expiration=None, actions=None,
                     network_ids=None, device_ids=None):
        return self._token.create(user_id, expiration, actions, network_ids,
                                  device_ids)

    def refresh_token(self):
        self._token.refresh()
        return self._token.access_token()

    def list_devices(self, **params):
        devices = Devices(self._transport, self._token)
        return devices.list(**params)

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

    def disconnect(self):
        if not self._transport.connected():
            return
        self._transport.disconnect()
