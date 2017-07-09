import uuid


class Transport(object):
    """Transport class."""

    REQUEST_ID_KEY = 'requestId'
    REQUEST_ACTION_KEY = 'action'

    def __init__(self, name, data_format_class, data_format_options,
                 handler_class, handler_options):
        self._name = name
        self._data_format = data_format_class(**data_format_options)
        self._data_type = self._data_format.data_type
        self._handler = handler_class(self, **handler_options)
        self._connected = False

    @staticmethod
    def _uuid():
        return str(uuid.uuid1())

    def _ensure_not_connected(self):
        if self._connected:
            raise TransportConnectionException('Connection has already created')

    def _ensure_connected(self):
        if not self._connected:
            raise TransportConnectionException('Connection has not created')

    def _encode(self, obj):
        return self._data_format.encode(obj)

    def _decode(self, data):
        return self._data_format.decode(data)

    def _call_handler_method(self, name, *args):
        getattr(self._handler, name)(*args)

    def name(self):
        return self._name

    def connected(self):
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


class TransportException(Exception):
    """Transport exception."""
    pass


class TransportConnectionException(TransportException):
    """Transport connection exception."""
    pass


class TransportRequestException(TransportException):
    """Transport request exception."""
    pass
