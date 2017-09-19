from devicehive import Handler
from devicehive import DeviceHive
import logging.config


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '[%(levelname)s] %(asctime)s: %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True
        },
        'devicehive.api_request': {
            'handlers': ['console'],
            'level': 'INFO',
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


url = 'http://playground.dev.devicehive.com/api/rest'
refresh_token = 'PUT_YOUR_REFRESH_TOKEN_HERE'
dh = DeviceHive(EchoHandler)
dh.connect(url, refresh_token=refresh_token)
