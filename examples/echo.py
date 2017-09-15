from devicehive import Handler
from devicehive import DeviceHive


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
