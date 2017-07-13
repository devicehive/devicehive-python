from builtins import str


def test_get(test):

    def handle_connect(handler):
        info = handler.api.get_info()
        assert isinstance(info['api_version'], str)
        assert isinstance(info['server_timestamp'], str)
        if info.get('rest_server_url'):
            assert info['websocket_server_url'] is None
            assert isinstance(info['rest_server_url'], str)
            return
        assert isinstance(info['websocket_server_url'], str)
        assert info['rest_server_url'] is None

    test.run(handle_connect)
