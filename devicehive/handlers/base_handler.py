class BaseHandler(object):
    """Base handler class."""

    def __init__(self, transport):
        self.transport = transport

    def handle_connected(self):
        raise NotImplementedError

    def handle_event(self, obj):
        raise NotImplementedError

    def handle_closed(self):
        raise NotImplementedError
