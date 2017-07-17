from devicehive.api_object import ApiObject
from devicehive.device import Device


class Devices(ApiObject):
    """Devices class."""

    def __init__(self, transport, token):
        ApiObject.__init__(self, transport)
        self._token = token

    def list(self, name=None, name_pattern=None, network_id=None,
             network_name=None, sort_field=None, sort_order=None, take=None,
             skip=None):
        url = 'device'
        action = 'device/list'
        request = {}
        params = {'response_key': 'devices'}
        self._set_request_param('name', name, request, params)
        self._set_request_param('namePattern', name_pattern, request, params)
        self._set_request_param('networkId', network_id, request, params)
        self._set_request_param('networkName', network_name, request, params)
        self._set_request_param('sortField', sort_field, request, params)
        self._set_request_param('sortOrder', sort_order, request, params)
        self._set_request_param('take', take, request, params)
        self._set_request_param('skip', skip, request, params)
        response = self._token.authorized_request(url, action, request,
                                                  **params)
        self._ensure_success_response(response, 'List devices failure')
        devices = response.response('devices')
        return [Device(self._transport, self._token, device)
                for device in devices]
