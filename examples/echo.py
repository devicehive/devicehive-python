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


from devicehive import Handler
from devicehive import DeviceHive
import logging.config


LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'devicehive.api_request': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False
        },
    }
}

logging.config.dictConfig(LOGGING)


class EchoHandler(Handler):

    def __init__(self, api, device_id='example-echo-device'):
        super(EchoHandler, self).__init__(api)
        self._device_id = device_id
        self._device = None

    def handle_connect(self):
        self._device = self.api.put_device(self._device_id)
        self._device.subscribe_insert_commands()

    def handle_command_insert(self, command):
        self._device.send_notification(command.command,
                                       parameters=command.parameters)


url = 'http://playground-dev.devicehive.com/api/rest'
refresh_token = 'PUT_YOUR_REFRESH_TOKEN_HERE'
dh = DeviceHive(EchoHandler)
dh.connect(url, refresh_token=refresh_token)
