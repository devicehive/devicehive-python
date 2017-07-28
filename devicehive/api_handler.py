from devicehive.handlers.handler import Handler
from devicehive.api import Api
from devicehive.command import Command


class ApiHandler(Handler):
    """Api handler class."""

    EVENT_ACTION_KEY = 'action'
    EVENT_SUBSCRIPTION_ID_KEY = 'subscriptionId'
    EVENT_COMMAND_INSERT_ACTION = 'command/insert'
    EVENT_COMMAND_UPDATE_ACTION = 'command/update'
    EVENT_COMMAND_KEY = 'command'

    def __init__(self, transport, auth, handler_class, handler_options):
        Handler.__init__(self, transport)
        self._api = Api(self._transport, auth)
        self._handler = handler_class(self._api, handler_options)
        self._handle_connect = False

    def handle_connect(self):
        self._api.auth()
        self._api.server_timestamp = self._api.get_info()['server_timestamp']
        if not self._handle_connect:
            self._handler.handle_connect()
            self._handle_connect = True

    def handle_event(self, event):
        subscription_id = event.get(self.EVENT_SUBSCRIPTION_ID_KEY)
        if event[self.EVENT_ACTION_KEY] == self.EVENT_COMMAND_INSERT_ACTION:
            command = Command(self._api, event[self.EVENT_COMMAND_KEY])
            self._handler.handle_command_insert(subscription_id, command)
        if event[self.EVENT_ACTION_KEY] == self.EVENT_COMMAND_UPDATE_ACTION:
            command = Command(self._api, event[self.EVENT_COMMAND_KEY])
            self._handler.handle_command_update(subscription_id, command)

    def handle_disconnect(self):
        # TODO: handle disconnect here.
        pass
