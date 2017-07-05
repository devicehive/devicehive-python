from devicehive.api import Token


class Handler(object):
    """Handler class."""

    def __init__(self, transport, authentication, options):
        self._transport = transport
        self._authentication = authentication
        self.token = Token(transport, authentication)
        self.options = options

    def create_token(self, user_id, expiration=None, actions=None,
                     network_ids=None, device_ids=None):
        return self.token.create(user_id, expiration, actions, network_ids,
                                 device_ids)

    def refresh_token(self):
        self.token.refresh()
        return self.token.access_token()

    def handle_connected(self):
        raise NotImplementedError

    def handle_event(self, event):
        raise NotImplementedError
