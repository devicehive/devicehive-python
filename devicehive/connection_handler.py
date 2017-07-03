from devicehive.handlers.base_handler import BaseHandler
from devicehive.api import Api


class ConnectionHandler(BaseHandler):
    """Connection handler class."""

    def __init__(self, transport, handler_class=None, handler_options=None,
                 refresh_token=None, access_token=None):
        assert handler_class is not None, 'Handler class required'
        assert refresh_token is not None, 'Refresh token required'
        BaseHandler.__init__(self, transport)
        self.api = Api(transport)
        self._handler = handler_class(self.api, handler_options)
        self._refresh_token = refresh_token
        self._access_token = access_token

    def handle_connected(self):
        if not self._access_token:
            response = self.api.refresh_token(self._refresh_token)
            self._access_token = response.data['accessToken']

    def handle_event(self, event):
        # TODO: handle event here and call handler method.
        pass

    def handle_closed(self):
        # TODO: reconnect here.
        pass
