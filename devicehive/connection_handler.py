from devicehive.handlers.base_handler import BaseHandler
from devicehive.api import Token


class ConnectionHandler(BaseHandler):
    """Connection handler class."""

    def __init__(self, transport, handler_class, handler_options,
                 authentication):
        BaseHandler.__init__(self, transport)
        self._token = Token(transport, authentication)
        self._handler = handler_class(transport, self._token, handler_options)
        self._handle_connected = False

    def handle_connected(self):
        self._token.authenticate()
        if not self._handle_connected:
            self._handler.handle_connected()
            self._handle_connected = True

    def handle_event(self, event):
        # TODO: handle events here.
        pass

    def handle_closed(self):
        # TODO: handle closed here.
        pass
