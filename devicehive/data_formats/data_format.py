class DataFormat(object):
    """Data format class."""

    def __init__(self, data_type):
        self.data_type = data_type

    def encode(self, data):
        raise NotImplementedError

    def decode(self, data):
        raise NotImplementedError
