from devicehive.api_object import ApiObject


class Device(ApiObject):
    """Device class."""

    ID_KEY = 'id'
    NAME_KEY = 'name'
    DATA_KEY = 'data'
    NETWORK_ID_KEY = 'networkId'
    IS_BLOCKED_KEY = 'isBlocked'

    def __init__(self, transport, token, device=None):
        ApiObject.__init__(self, transport)
        self._token = token
        self._id = None
        self.name = None
        self.data = None
        self.network_id = None
        self.is_blocked = None
        if device:
            self._init(device)

    def _init(self, device):
        self._id = device[self.ID_KEY]
        self.name = device[self.NAME_KEY]
        self.data = device[self.DATA_KEY]
        self.network_id = device[self.NETWORK_ID_KEY]
        self.is_blocked = device[self.IS_BLOCKED_KEY]

    def id(self):
        return self._id

    def get(self, device_id):
        url = 'device/%s' % device_id
        action = 'device/get'
        request = {'deviceId': device_id}
        params = {'request_delete_keys': ['deviceId'], 'response_key': 'device'}
        response = self._token.authorized_request(url, action, request,
                                                  **params)
        self._ensure_success_response(response, 'Device get failure')
        device = response.response('device')
        self._init(device)

    def save(self):
        url = 'device/%s' % self._id
        action = 'device/save'
        device = {self.ID_KEY: self._id,
                  self.NAME_KEY: self.name,
                  self.DATA_KEY: self.data,
                  self.NETWORK_ID_KEY: self.network_id,
                  self.IS_BLOCKED_KEY: self.is_blocked}
        request = {'deviceId': self._id, 'device': device}
        params = {'method': 'PUT', 'request_key': 'device'}
        response = self._token.authorized_request(url, action, request,
                                                  **params)
        self._ensure_success_response(response, 'Device save failure')

    def remove(self):
        # TODO: implement websocket support when API will be added.
        self._ensure_http_transport()
        url = 'device/%s' % self._id
        action = None
        request = {}
        params = {'method': 'DELETE'}
        response = self._token.authorized_request(url, action, request,
                                                  **params)
        self._ensure_success_response(response, 'Device remove failure')
        self._id = None
        self.name = None
        self.data = None
        self.network_id = None
        self.is_blocked = None
