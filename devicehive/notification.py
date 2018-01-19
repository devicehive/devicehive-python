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


class Notification(object):
    """Notification class."""

    DEVICE_ID_KEY = 'deviceId'
    ID_KEY = 'id'
    NOTIFICATION_KEY = 'notification'
    PARAMETERS_KEY = 'parameters'
    TIMESTAMP_KEY = 'timestamp'

    def __init__(self, notification):
        self._device_id = notification[self.DEVICE_ID_KEY]
        self._id = notification[self.ID_KEY]
        self._notification = notification[self.NOTIFICATION_KEY]
        self._parameters = notification[self.PARAMETERS_KEY]
        self._timestamp = notification[self.TIMESTAMP_KEY]

    @property
    def device_id(self):
        return self._device_id

    @property
    def id(self):
        return self._id

    @property
    def notification(self):
        return self._notification

    @property
    def parameters(self):
        return self._parameters

    @property
    def timestamp(self):
        return self._timestamp
