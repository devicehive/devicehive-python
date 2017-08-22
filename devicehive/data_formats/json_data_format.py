from devicehive.data_formats.data_format import DataFormat
import json


class JsonDataFormat(DataFormat):
    """Json data format class."""

    def __init__(self):
        DataFormat.__init__(self, 'json', self.TEXT_DATA_TYPE)

    def encode(self, data):
        return json.dumps(data)

    def decode(self, data):
        return json.loads(data)
