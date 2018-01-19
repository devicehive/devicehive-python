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


class ApiEvent(object):
    """Api event class."""

    EVENT_ACTION_KEY = 'action'
    EVENT_SUBSCRIPTION_ID_KEY = 'subscriptionId'

    def __init__(self, event):
        self._action = event.pop(self.EVENT_ACTION_KEY)
        self._subscription_id = event.pop(self.EVENT_SUBSCRIPTION_ID_KEY)
        self._event = event

    @property
    def action(self):
        return self._action

    @property
    def subscription_id(self):
        return self._subscription_id

    @property
    def event(self):
        return self._event
