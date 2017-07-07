from devicehive.handlers.base_handler import BaseHandler
from devicehive.api import Api


class ConnectionHandler(BaseHandler):
    """Connection handler class."""

    def __init__(self, transport, authentication, handler_class,
                 handler_options):
        BaseHandler.__init__(self, transport)
        self._api = Api(self.transport, authentication)
        self._handler = handler_class(self._api, handler_options)
        self._handle_connected = False

    def handle_connect(self):
        self._api.authenticate()
        if not self._handle_connected:
            self._handler.handle_connected()
            self._handle_connected = True

    def handle_event(self, event):
        # TODO: handle events here.
        pass

    def handle_closed(self):
        # TODO: handle closed here.
        pass
