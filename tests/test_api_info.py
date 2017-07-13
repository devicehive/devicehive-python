from tests.types import string
from tests.conftest import not_implemented_skip


def test_get(test):

    def handle_connect(handler):
        info = handler.api.get_info()
        assert isinstance(info['api_version'], string)
        assert isinstance(info['server_timestamp'], string)
        if info.get('rest_server_url'):
            assert info['websocket_server_url'] is None
            assert isinstance(info['rest_server_url'], string)
            return
        assert isinstance(info['websocket_server_url'], string)
        assert info['rest_server_url'] is None

    test.run(handle_connect)


@not_implemented_skip
def test_get_cluster(test):
    pass
