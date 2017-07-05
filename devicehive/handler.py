from devicehive.api import Device


class Handler(object):
    """Handler class."""

    def __init__(self, transport, token, options):
        self._transport = transport
        self._token = token
        self.options = options

    def create_token(self, user_id, expiration=None, actions=None,
                     network_ids=None, device_ids=None):
        return self._token.create(user_id, expiration, actions, network_ids,
                                  device_ids)

    def refresh_token(self):
        self._token.refresh()
        return self._token.access_token()

    def get_device(self, device_id):
        device = Device(self._transport, self._token)
        device.get(device_id)
        if device.id:
            return device

    def handle_connected(self):
        raise NotImplementedError

    def handle_event(self, event):
        raise NotImplementedError
