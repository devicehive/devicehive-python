from devicehive.data_formats.base_data_format import BaseDataFormat
import json


class JsonDataFormat(BaseDataFormat):
    """Json data format class."""

    def __init__(self):
        BaseDataFormat.__init__(self, 'text')

    def encode(self, data):
        return json.dumps(data)

    def decode(self, data):
        return json.loads(data)
