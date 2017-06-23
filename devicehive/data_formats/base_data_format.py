class BaseDataFormat(object):
    """Base data format class."""

    def __init__(self, data_type, **options):
        self.data_type = data_type

    def encode(self, data):
        raise NotImplementedError

    def decode(self, data):
        raise NotImplementedError
