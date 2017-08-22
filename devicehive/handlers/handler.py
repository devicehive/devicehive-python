class Handler(object):
    """Handler class."""

    def __init__(self, transport):
        self._transport = transport

    def handle_connect(self):
        raise NotImplementedError

    def handle_event(self, event):
        raise NotImplementedError

    def handle_disconnect(self):
        raise NotImplementedError
