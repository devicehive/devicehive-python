class BaseDataFormat(object):
    """Base data format class."""

    def get_type(self):
        raise NotImplementedError

    def encode(self, data):
        raise NotImplementedError

    def decode(self, data):
        raise NotImplementedError
