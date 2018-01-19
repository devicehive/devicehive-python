# Copyright (C) 2018 DataArt
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================


from devicehive.handlers.handler import Handler
from devicehive.api import Api
from devicehive.api_event import ApiEvent
from devicehive.command import Command
from devicehive.notification import Notification


class ApiHandler(Handler):
    """Api handler class."""

    EVENT_COMMAND_INSERT_ACTION = 'command/insert'
    EVENT_COMMAND_UPDATE_ACTION = 'command/update'
    EVENT_COMMAND_KEY = 'command'
    EVENT_NOTIFICATION_ACTION = 'notification/insert'
    EVENT_NOTIFICATION_KEY = 'notification'

    def __init__(self, transport, auth, handler_class, handler_args,
                 handler_kwargs, api_init):
        super(ApiHandler, self).__init__(transport)
        self._api = Api(self._transport, auth)
        self._handler = handler_class(self._api, *handler_args,
                                      **handler_kwargs)
        self._api_init = api_init
        self._handle_connect = False

    @property
    def handler(self):
        return self._handler

    def handle_connect(self):
        self._api.token.auth()
        if self._api_init:
            server_timestamp = self._api.get_info()['server_timestamp']
            self._api.server_timestamp = server_timestamp
        if not self._handle_connect:
            self._handle_connect = True
            self._handler.handle_connect()
            return

    def handle_event(self, event):
        api_event = ApiEvent(event)
        action = api_event.action
        event = api_event.event
        if action == self.EVENT_COMMAND_INSERT_ACTION:
            command = Command(self._api, event[self.EVENT_COMMAND_KEY])
            return self._handler.handle_command_insert(command)
        if action == self.EVENT_COMMAND_UPDATE_ACTION:
            command = Command(self._api, event[self.EVENT_COMMAND_KEY])
            return self._handler.handle_command_update(command)
        if action == self.EVENT_NOTIFICATION_ACTION:
            notification = Notification(event[self.EVENT_NOTIFICATION_KEY])
            return self._handler.handle_notification(notification)

    def handle_disconnect(self):
        pass
