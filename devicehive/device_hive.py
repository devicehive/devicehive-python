from devicehive.data_formats.json_data_format import JsonDataFormat
from devicehive.connection_handler import ConnectionHandler
from devicehive.transport import init


class DeviceHive(object):
    """Device hive class."""

    def __init__(self, transport_url, handler_class, handler_options, **params):
        self._transport_name = params.get('transport_name', 'http')
        self._transport_url = transport_url
        self._data_format_class = JsonDataFormat
        self._data_format_options = {}
        self._handler_options = {'handler_class': handler_class,
                                 'handler_options': handler_options}
        self._transport_options = params.get('transport_options', {})

    def initialize(self, user_login=None, user_password=None,
                   refresh_token=None, access_token=None):
        authentication = {'user_login': user_login,
                          'user_password': user_password,
                          'refresh_token': refresh_token,
                          'access_token': access_token}
        self._handler_options['authentication'] = authentication
        transport = init(self._transport_name, self._data_format_class,
                         self._data_format_options, ConnectionHandler,
                         self._handler_options)
        transport.connect(self._transport_url, **self._transport_options)
        transport.join()
