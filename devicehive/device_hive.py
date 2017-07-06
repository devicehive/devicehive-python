from devicehive.data_formats.json_data_format import JsonDataFormat
from devicehive.connection_handler import ConnectionHandler


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
        self._data_format_class = JsonDataFormat
        self._data_format_options = {}
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
        self._transport = transport_class(self._data_format_class,
                                          self._data_format_options,
                                          ConnectionHandler,
                                          self._handler_options)

    def connect(self, user_login=None, user_password=None, refresh_token=None,
                access_token=None):
        authentication = {'user_login': user_login,
                          'user_password': user_password,
                          'refresh_token': refresh_token,
                          'access_token': access_token}
        self._handler_options['authentication'] = authentication
        self._init_transport()
        self._transport.connect(self._transport_url, **self._transport_options)

    def join(self):
        self._transport.join()
