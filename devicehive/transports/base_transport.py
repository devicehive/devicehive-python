import uuid


class BaseTransport(object):
    """Base transport class."""

    REQUEST_ID_KEY = 'requestId'
    REQUEST_ACTION_KEY = 'action'

    def __init__(self, data_format_class, data_format_options, handler_class,
                 handler_options, name):
        self._data_format = data_format_class(**data_format_options)
        self._data_type = self._data_format.data_type
        self._handler = handler_class(self, **handler_options)
        self._connected = False
        self._name = name

    @staticmethod
    def _uuid():
        return str(uuid.uuid1())

    def _assert_not_connected(self):
        assert not self._connected, 'transport connection already created'

    def _assert_connected(self):
        assert self._connected, 'transport connection has not created'

    def _encode(self, obj):
        return self._data_format.encode(obj)

    def _decode(self, data):
        return self._data_format.decode(data)

    def _call_handler_method(self, name, *args):
        getattr(self._handler, name)(*args)

    def name(self):
        return self._name

    def is_connected(self):
        return self._connected

    def connect(self, url, **options):
        raise NotImplementedError

    def send_request(self, action, request, **params):
        raise NotImplementedError

    def request(self, action, request, **params):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    def join(self, timeout=None):
        raise NotImplementedError


class BaseTransportException(Exception):
    """Base transport exception."""
    pass
