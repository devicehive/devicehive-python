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


import warnings


class Handler(object):
    """Handler class."""

    def __init__(self, api):
        self._api = api

    @property
    def api(self):
        return self._api

    def handle_connect(self):
        raise NotImplementedError

    def handle_command_insert(self, command):
        message = 'Inserted command received. Command id: %s.' % command.id
        warnings.warn(message, HandlerWarning)

    def handle_command_update(self, command):
        message = 'Updated command received. Command id: %s.' % command.id
        warnings.warn(message, HandlerWarning)

    def handle_notification(self, notification):
        message = 'Notification received. Notification id: %s.'
        message %= notification.id
        warnings.warn(message, HandlerWarning)


class HandlerWarning(UserWarning):
    """Handler warning."""
