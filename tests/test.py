from devicehive import Handler
from devicehive import DeviceHive


class TestHandler(Handler):
    """Test handler class."""

    def handle_connect(self):
        if not self.options['handle_connect'](self):
            self.api.disconnect()

    def handle_event(self, event):
        pass


class Test(object):
    """Test class."""

    def __init__(self, transport_url, refresh_token):
        self._transport_url = transport_url
        self._refresh_token = refresh_token

    def run(self, handle_connect, handle_event=None):
        handler_options = {'test': self,
                           'handle_connect': handle_connect,
                           'handle_event': handle_event}
        device_hive = DeviceHive(self._transport_url, TestHandler,
                                 handler_options)
        device_hive.connect(refresh_token=self._refresh_token)
        exception_info = device_hive.join(print_exception=False)
        if exception_info:
            raise exception_info[1]
