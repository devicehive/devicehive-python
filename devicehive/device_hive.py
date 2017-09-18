from devicehive.data_formats.json_data_format import JsonDataFormat
from devicehive.api_handler import ApiHandler
import time
import six


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
        connect_timeout = options.pop('connect_timeout', 30)
        max_num_connect = options.pop('max_num_connect', 10)
        connect_interval = options.pop('connect_interval', 1)
        transport_alive_timeout = options.pop('transport_alive_timeout', 0.01)
        self._api_handler_options['auth'] = auth
        self._init_transport()
        connect_time = time.time()
        num_connect = 0
        while True:
            if self._transport.connected:
                self._transport.disconnect()
            self._transport.connect(transport_url, **options)
            while self._transport.is_alive():
                time.sleep(transport_alive_timeout)
            exception_info = self._transport.exception_info
            if exception_info and not isinstance(exception_info[1],
                                                 self._transport.error):
                six.reraise(*exception_info)
            if not self._transport.handler.handler.api.connected:
                return
            if time.time() - connect_time < connect_timeout:
                num_connect += 1
                if num_connect > max_num_connect:
                    six.reraise(*exception_info)
                time.sleep(connect_interval)
                continue
            connect_time = time.time()
            num_connect = 0
