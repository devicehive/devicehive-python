# Copyright (C) 2018 DataArt
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================


class DataFormat(object):
    """Data format class."""

    TEXT_DATA_TYPE = 'text'
    BINARY_DATA_TYPE = 'binary'

    def __init__(self, name, data_type):
        self._name = name
        self._data_type = data_type

    @property
    def name(self):
        return self._name

    @property
    def data_type(self):
        return self._data_type

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
