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
        # TODO: implement params for websocket when API will be extended.
        url = 'device'
        action = 'device/list'
        request = {}
        params = {'response_key': 'devices', 'params': {}}
        if name:
            params['params']['name'] = name
        if name_pattern:
            params['params']['namePattern'] = name_pattern
        if network_id:
            params['params']['networkId'] = network_id
        if network_name:
            params['params']['networkName'] = network_name
        if sort_field:
            params['params']['sortField'] = sort_field
        if sort_order:
            params['params']['sortOrder'] = sort_order
        if take:
            params['params']['take'] = take
        if skip:
            params['params']['skip'] = skip
        response = self._token.authorized_request(url, action, request,
                                                  **params)
        self._ensure_success_response(response, 'List devices failure')
        devices = response.response('devices')
        return [Device(self._transport, self._token, device)
                for device in devices]
