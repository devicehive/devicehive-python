class Handler(object):
    """Handler class."""

    def __init__(self, transport, token, options):
        self._transport = transport
        self._token = token
        self.options = options

    def handle_connected(self):
        raise NotImplementedError

    def handle_event(self, event):
        raise NotImplementedError
