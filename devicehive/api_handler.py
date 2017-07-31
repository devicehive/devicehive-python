from devicehive.handlers.handler import Handler
from devicehive.api import Api
from devicehive.api_event import ApiEvent
from devicehive.command import Command


class ApiHandler(Handler):
    """Api handler class."""

    EVENT_COMMAND_INSERT_ACTION = 'command/insert'
    EVENT_COMMAND_UPDATE_ACTION = 'command/update'
    EVENT_COMMAND_KEY = 'command'

    def __init__(self, transport, auth, handler_class, handler_args,
                 handler_kwargs):
        Handler.__init__(self, transport)
        self._api = Api(self._transport, auth)
        self._handler = handler_class(self._api, *handler_args,
                                      **handler_kwargs)
        self._handle_connect = False

    def handle_connect(self):
        self._api.token.auth()
        self._api.server_timestamp = self._api.get_info()['server_timestamp']
        if not self._handle_connect:
            self._handler.handle_connect()
            self._handle_connect = True

    def handle_event(self, event):
        api_event = ApiEvent(event)
        action = api_event.action
        subscription_id = api_event.subscription_id
        event = api_event.event
        if action == self.EVENT_COMMAND_INSERT_ACTION:
            command = Command(self._api, event[self.EVENT_COMMAND_KEY])
            return self._handler.handle_command_insert(subscription_id, command)
        if action == self.EVENT_COMMAND_UPDATE_ACTION:
            command = Command(self._api, event[self.EVENT_COMMAND_KEY])
            return self._handler.handle_command_update(subscription_id, command)

    def handle_disconnect(self):
        # TODO: handle disconnect here.
        pass
