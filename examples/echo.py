from devicehive import Handler
from devicehive import DeviceHive


class EchoHandler(Handler):

    def handle_connect(self):
        info = self.api.get_info()
        print(info)
        self.api.disconnect()


url = 'http://playground.dev.devicehive.com/api/rest'
refresh_token = 'PUT_YOUR_REFRESH_TOKEN_HERE'
dh = DeviceHive(EchoHandler)
dh.connect(url, refresh_token=refresh_token)
