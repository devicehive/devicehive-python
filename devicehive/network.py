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


from devicehive.api_request import AuthApiRequest
from devicehive.api_request import ApiRequestError


class Network(object):
    """Network class."""

    ID_KEY = 'id'
    NAME_KEY = 'name'
    DESCRIPTION_KEY = 'description'

    def __init__(self, api, network=None):
        self._api = api
        self._id = None
        self.name = None
        self.description = None
        if network:
            self._init(network)

    def _init(self, device):
        self._id = device[self.ID_KEY]
        self.name = device[self.NAME_KEY]
        self.description = device[self.DESCRIPTION_KEY]

    def _ensure_exists(self):
        if self._id:
            return
        raise NetworkError('Network does not exist.')

    @property
    def id(self):
        return self._id

    def get(self, network_id):
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.url('network/{networkId}', networkId=network_id)
        auth_api_request.action('network/get')
        auth_api_request.response_key('network')
        network = auth_api_request.execute('Network get failure.')
        self._init(network)

    def save(self):
        self._ensure_exists()
        network = {self.ID_KEY: self._id,
                   self.NAME_KEY: self.name,
                   self.DESCRIPTION_KEY: self.description}
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.method('PUT')
        auth_api_request.url('network/{networkId}', networkId=self._id)
        auth_api_request.action('network/update')
        auth_api_request.set('network', network, True)
        auth_api_request.execute('Network save failure.')

    def remove(self):
        self._ensure_exists()
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.method('DELETE')
        auth_api_request.url('network/{networkId}', networkId=self._id)
        auth_api_request.action('network/delete')
        auth_api_request.execute('Network remove failure.')
        self._id = None
        self.name = None
        self.description = None

    def list_devices(self, name=None, name_pattern=None, sort_field=None,
                     sort_order=None, take=None, skip=None):
        self._ensure_exists()
        return self._api.list_devices(name, name_pattern, self._id, self.name,
                                      sort_field, sort_order, take, skip)

    def subscribe_insert_commands(self, names=(), timestamp=None):
        self._ensure_exists()
        return self._api.subscribe_insert_commands(network_ids=[self.id],
                                                   names=names,
                                                   timestamp=timestamp)

    def subscribe_update_commands(self, names=(), timestamp=None):
        self._ensure_exists()
        return self._api.subscribe_update_commands(network_ids=[self.id],
                                                   names=names,
                                                   timestamp=timestamp)

    def subscribe_notifications(self, names=(), timestamp=None):
        self._ensure_exists()
        return self._api.subscribe_notifications(network_ids=[self.id],
                                                 names=names,
                                                 timestamp=timestamp)


class NetworkError(ApiRequestError):
    """Network error."""
