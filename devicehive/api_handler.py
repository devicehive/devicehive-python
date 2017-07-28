from devicehive.handlers.handler import Handler
from devicehive.token import Token
from devicehive.api import Api


class ApiHandler(Handler):
    """Api handler class."""

    def __init__(self, transport, auth, handler_class, handler_options):
        Handler.__init__(self, transport)
        self._token = Token(self._transport, auth)
        self._api = Api(self._transport, self._token)
        self._handler = handler_class(self._api, handler_options)
        self._handle_connect = False

    def handle_connect(self):
        self._token.auth()
        if not self._handle_connect:
            self._handler.handle_connect()
            self._handle_connect = True

    def handle_event(self, event):
        # TODO: handle events here.
        pass

    def handle_disconnect(self):
        # TODO: handle disconnect here.
        pass
