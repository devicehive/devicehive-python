from devicehive.api_object import ApiObject


class Info(ApiObject):
    """Info class."""

    def get(self):
        url = 'info'
        action = 'server/info'
        request = {}
        params = {'response_key': 'info'}
        response = self._request(url, action, request, **params)
        self._ensure_success_response(response, 'Info get failure')
        info = response.response('info')
        return {'api_version': info['apiVersion'],
                'server_timestamp': info['serverTimestamp'],
                'rest_server_url': info.get('restServerUrl'),
                'websocket_server_url': info.get('webSocketServerUrl')}

    def get_cluster_info(self):
        # TODO: implement websocket support when API will be added.
        self._ensure_http_transport()
        url = 'info/config/cluster'
        action = None
        request = {}
        params = {'response_key': 'cluster_info'}
        response = self._request(url, action, request, **params)
        self._ensure_success_response(response, 'Cluster info get failure')
        return response.response('cluster_info')
