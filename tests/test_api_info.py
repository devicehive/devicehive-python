from six import string_types


def test_get(test):

    def handle_connect(handler):
        info = handler.api.get_info()
        assert isinstance(info['api_version'], string_types)
        assert isinstance(info['server_timestamp'], string_types)
        if info.get('rest_server_url'):
            assert info['websocket_server_url'] is None
            assert isinstance(info['rest_server_url'], string_types)
            return
        assert isinstance(info['websocket_server_url'], string_types)
        assert info['rest_server_url'] is None

    test.run(handle_connect)


def test_get_cluster(test):

    def handle_connect(handler):
        cluster_info = handler.api.get_cluster_info()
        assert isinstance(cluster_info['bootstrap.servers'], string_types)
        assert isinstance(cluster_info['zookeeper.connect'], string_types)

    test.run(handle_connect)
