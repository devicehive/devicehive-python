from devicehive.data_formats.json_data_format import JsonDataFormat
from devicehive.connection_handler import ConnectionHandler
import traceback


class DeviceHive(object):
    """Device hive class."""

    def __init__(self, handler_class, handler_options):
        self._handler_options = {'handler_class': handler_class,
                                 'handler_options': handler_options}
        self._transport_name = None
        self._transport = None

    def _init_transport(self):
        name = 'devicehive.transports.%s_transport' % self._transport_name
        class_name = '%sTransport' % self._transport_name.title()
        transport_module = __import__(name, globals(), locals(), [name])
        transport_class = getattr(transport_module, class_name)
        self._transport = transport_class(JsonDataFormat, {}, ConnectionHandler,
                                          self._handler_options)

    @staticmethod
    def transport_name(transport_url):
        if transport_url[0:4] == 'http':
            return 'http'
        if transport_url[0:2] == 'ws':
            return 'websocket'

    def connect(self, transport_url, **options):
        self._transport_name = self.transport_name(transport_url)
        assert self._transport_name, 'Unexpected transport url scheme'
        authentication = {'login': options.pop('login', None),
                          'password': options.pop('password', None),
                          'refresh_token': options.pop('refresh_token', None),
                          'access_token': options.pop('access_token', None)}
        self._handler_options['authentication'] = authentication
        self._init_transport()
        self._transport.connect(transport_url, **options)

    def join(self, timeout=None, print_exception=True):
        self._transport.join(timeout)
        exception_info = self._transport.exception_info()
        if not exception_info:
            return
        if print_exception:
            traceback.print_exception(exception_info[0], exception_info[1],
                                      exception_info[2])
        return exception_info
