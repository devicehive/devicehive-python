from devicehive.handlers.handler import Handler
from devicehive.api import Api


class ConnectionHandler(Handler):
    """Connection handler class."""

    def __init__(self, transport, authentication, handler_class,
                 handler_options):
        Handler.__init__(self, transport)
        self._api = Api(self.transport, authentication)
        self._handler = handler_class(self._api, handler_options)
        self._handle_connect = False

    def handle_connect(self):
        self._api.authenticate()
        if not self._handle_connect:
            self._handler.handle_connect()
            self._handle_connect = True

    def handle_event(self, event):
        # TODO: handle events here.
        pass

    def handle_close(self):
        # TODO: handle close here.
        pass
