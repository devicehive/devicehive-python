from devicehive.data_formats.json_data_format import JsonDataFormat
from devicehive.api_handler import ApiHandler
import traceback


class DeviceHive(object):
    """Device hive class."""

    def __init__(self, handler_class, *handler_args, **handler_kwargs):
        self._api_handler_options = {'handler_class': handler_class,
                                     'handler_args': handler_args,
                                     'handler_kwargs': handler_kwargs}
        self._transport_name = None
        self._transport = None

    def _init_transport(self):
        name = 'devicehive.transports.%s_transport' % self._transport_name
        class_name = '%sTransport' % self._transport_name.title()
        transport_module = __import__(name, globals(), locals(), [name])
        transport_class = getattr(transport_module, class_name)
        self._transport = transport_class(JsonDataFormat, {}, ApiHandler,
                                          self._api_handler_options)

    @staticmethod
    def transport_name(transport_url):
        if transport_url[0:4] == 'http':
            return 'http'
        if transport_url[0:2] == 'ws':
            return 'websocket'

    def connect(self, transport_url, **options):
        self._transport_name = self.transport_name(transport_url)
        assert self._transport_name, 'Unexpected transport url scheme'
        auth = {'login': options.pop('login', None),
                'password': options.pop('password', None),
                'refresh_token': options.pop('refresh_token', None),
                'access_token': options.pop('access_token', None)}
        self._api_handler_options['auth'] = auth
        self._init_transport()
        self._transport.connect(transport_url, **options)

    def join(self, timeout=None):
        self._transport.join(timeout)

    def exception_info(self):
        return self._transport.exception_info

    def print_exception(self):
        transport_exception_info = self._transport.exception_info
        if not transport_exception_info:
            return
        traceback.print_exception(transport_exception_info[0],
                                  transport_exception_info[1],
                                  transport_exception_info[2])
