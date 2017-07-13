from devicehive.data_formats.json_data_format import JsonDataFormat
from devicehive.connection_handler import ConnectionHandler
import traceback


class DeviceHive(object):
    """Device hive class."""

    def __init__(self, transport_url, handler_class, handler_options, **params):
        self._transport_name = None
        if transport_url[0:4] == 'http':
            self._transport_name = 'http'
        if transport_url[0:2] == 'ws':
            self._transport_name = 'websocket'
        assert self._transport_name is not None, 'Unexpected url scheme'
        self._transport_url = transport_url
        self._handler_options = {'handler_class': handler_class,
                                 'handler_options': handler_options}
        self._transport_options = params.get('transport_options', {})
        self._transport = None

    def _init_transport(self):
        transport_class_name = '%sTransport' % self._transport_name.title()
        transport_module = __import__(
            'devicehive.transports.%s_transport' % self._transport_name,
            fromlist=[transport_class_name])
        transport_class = getattr(transport_module, transport_class_name)
        self._transport = transport_class(JsonDataFormat, {}, ConnectionHandler,
                                          self._handler_options)

    def connect(self, login=None, password=None, refresh_token=None,
                access_token=None):
        authentication = {'login': login,
                          'password': password,
                          'refresh_token': refresh_token,
                          'access_token': access_token}
        self._handler_options['authentication'] = authentication
        self._init_transport()
        self._transport.connect(self._transport_url, **self._transport_options)

    def join(self, timeout=None):
        self._transport.join(timeout)
        exception = self._transport.exception_info()
        if not exception:
            return
        traceback.print_exception(exception[0], exception[1], exception[2])
