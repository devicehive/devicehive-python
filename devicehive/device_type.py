from devicehive.api_request import AuthApiRequest
from devicehive.api_request import ApiRequestError


class DeviceType(object):
    """DeviceType class."""

    ID_KEY = 'id'
    NAME_KEY = 'name'
    DESCRIPTION_KEY = 'description'

    def __init__(self, api, device_type=None):
        self._api = api
        self._id = None
        self.name = None
        self.description = None
        if device_type:
            self._init(device_type)

    def _init(self, device):
        self._id = device[self.ID_KEY]
        self.name = device[self.NAME_KEY]
        self.description = device[self.DESCRIPTION_KEY]

    def _ensure_exists(self):
        if self._id:
            return
        raise DeviceTypeError('DeviceType does not exist.')

    @property
    def id(self):
        return self._id

    def get(self, device_type_id):
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.url('devicetype/{deviceTypeId}',
                             deviceTypeId=device_type_id)
        auth_api_request.action('devicetype/get')
        auth_api_request.response_key('deviceType')
        devicetype = auth_api_request.execute('DeviceType get failure.')
        self._init(devicetype)

    def save(self):
        self._ensure_exists()
        device_type = {self.ID_KEY: self._id,
                       self.NAME_KEY: self.name,
                       self.DESCRIPTION_KEY: self.description}
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.method('PUT')
        auth_api_request.url('devicetype/{deviceTypeId}', deviceTypeId=self._id)
        auth_api_request.action('devicetype/update')
        auth_api_request.set('deviceType', device_type, True)
        auth_api_request.execute('DeviceType save failure.')

    def remove(self):
        self._ensure_exists()
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.method('DELETE')
        auth_api_request.url('devicetype/{deviceTypeId}', deviceTypeId=self._id)
        auth_api_request.action('devicetype/delete')
        auth_api_request.execute('DeviceType remove failure.')
        self._id = None
        self.name = None
        self.description = None

    def list_devices(self, name=None, name_pattern=None, sort_field=None,
                     sort_order=None, take=None, skip=None):
        self._ensure_exists()
        return self._api.list_devices(name, name_pattern, self._id, self.name,
                                      sort_field, sort_order, take, skip)


class DeviceTypeError(ApiRequestError):
    """DeviceType error."""
