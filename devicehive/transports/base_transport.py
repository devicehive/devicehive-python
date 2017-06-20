class BaseTransport(object):
    """Base transport class."""

    def __init__(self, name, data_format_class, data_format_options,
                 handler_class, handler_options):
        self._name = name
        self._data_format = data_format_class(**data_format_options)
        self._handler = handler_class(**handler_options)
        self._connected = False

    def _assert_not_connected(self):
        assert not self._connected, 'transport connection already created'

    def _assert_connected(self):
        assert self._connected, 'transport connection has not created'

    def _encode_obj(self, obj):
        return self._data_format.encode(obj)

    def _data_type(self):
        return self._data_format.get_type()

    def _decode_data(self, data):
        return self._data_format.decode(data)

    def _call_handler_method(self, name, *args):
        getattr(self._handler, name)(self, *args)

    def is_connected(self):
        return self._connected

    def connect(self, url, **options):
        raise NotImplementedError

    def request(self, action, request_object, **params):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    def join(self, timeout=None):
        raise NotImplementedError
