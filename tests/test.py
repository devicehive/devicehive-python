from devicehive import Handler
from devicehive import DeviceHive
import pytest


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
        self._transport_name = DeviceHive.transport_name(self._transport_url)

    def transport_name(self):
        return self._transport_name

    def http_transport(self):
        return self._transport_name == 'http'

    def websocket_transport(self):
        return self._transport_name == 'websocket'

    def only_http_implementation(self):
        if self.http_transport():
            return
        pytest.skip('Implemented only for http transport')

    def only_websocket_implementation(self):
        if self.websocket_transport():
            return
        pytest.skip('Implemented only for websocket transport')

    def run(self, handle_connect, handle_event=None):
        handler_options = {'handle_connect': handle_connect,
                           'handle_event': handle_event}
        device_hive = DeviceHive(TestHandler, handler_options)
        device_hive.connect(self._transport_url,
                            refresh_token=self._refresh_token)
        device_hive.join()
        exception_info = device_hive.exception_info()
        if not exception_info:
            return
        raise exception_info[1]
