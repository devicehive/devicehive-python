from devicehive.data_formats.json_data_format import JsonDataFormat
from devicehive.connection_handler import ConnectionHandler
import traceback


class DeviceHive(object):
    """Device hive class."""

    def __init__(self, transport_url, handler_class, handler_options, **params):
        self._transport_name = self.transport_name(transport_url)
        assert self._transport_name, 'Unexpected url scheme'
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

    @staticmethod
    def transport_name(transport_url):
        if transport_url[0:4] == 'http':
            return 'http'
        if transport_url[0:2] == 'ws':
            return 'websocket'

    def connect(self, login=None, password=None, refresh_token=None,
                access_token=None):
        authentication = {'login': login,
                          'password': password,
                          'refresh_token': refresh_token,
                          'access_token': access_token}
        self._handler_options['authentication'] = authentication
        self._init_transport()
        self._transport.connect(self._transport_url, **self._transport_options)

    def join(self, timeout=None, print_exception=True):
        self._transport.join(timeout)
        exception_info = self._transport.exception_info()
        if not exception_info:
            return
        if print_exception:
            traceback.print_exception(exception_info[0], exception_info[1],
                                      exception_info[2])
        return exception_info
