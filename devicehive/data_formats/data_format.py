class DataFormat(object):
    """Data format class."""

    TEXT_DATA_TYPE = 'text'
    BINARY_DATA_TYPE = 'binary'

    def __init__(self, data_type):
        self._data_type = data_type

    @property
    def text_data_type(self):
        return self._data_type == self.TEXT_DATA_TYPE

    @property
    def binary_data_type(self):
        return self._data_type == self.BINARY_DATA_TYPE

    def encode(self, data):
        raise NotImplementedError

    def decode(self, data):
        raise NotImplementedError
