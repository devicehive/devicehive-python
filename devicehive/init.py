from devicehive.data_formats.json_data_format import JsonDataFormat
from devicehive.connection_handler import ConnectionHandler
from devicehive.transport import init


def run(transport_name, transport_url, handler_class, handler_options,
        refresh_token, **params):
    data_format_class = params.get('data_format', JsonDataFormat)
    data_format_options = params.get('data_format_options', {})
    access_token = params.get('access_token', None)
    handler_options = {'handler_class': handler_class,
                       'handler_options': handler_options,
                       'refresh_token': refresh_token,
                       'access_token': access_token}
    transport_connect_options = params.get('connect_options', {})
    transport = init(transport_name, data_format_class, data_format_options,
                     ConnectionHandler, handler_options)
    transport.connect(transport_url, **transport_connect_options)
    transport.join()
