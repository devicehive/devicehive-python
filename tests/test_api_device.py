from devicehive.api_object import ApiObjectResponseException
import pytest


def test_get(test):

    def handle_connect(handler):
        device_id = 'test-api-get-id-%s' % test.transport_name()
        name = 'test-api-get-name-%s' % test.transport_name()
        data = {'key': 'value'}
        handler.api.put_device(device_id, name=name, data=data)
        device = handler.api.get_device(device_id)
        assert device.id() == device_id
        assert device.name == name
        assert device.data == data
        assert isinstance(device.network_id, int)
        assert not device.is_blocked
        # TODO: implement websocket support when API will be added.
        if test.http_transport():
            device.remove()

    test.run(handle_connect)


def test_get_not_exist(test):

    def handle_connect(handler):
        device_id = 'test-api-get-not-exist-%s' % test.transport_name()
        try:
            handler.api.get_device(device_id)
        except ApiObjectResponseException as api_object_response_exception:
            # TODO: test for 404 for all transports after bug will be fixed.
            if test.websocket_transport():
                assert api_object_response_exception.code() == 404
            if test.http_transport():
                assert api_object_response_exception.code() == 401
            pytest.xfail('Device does not exist')

    test.run(handle_connect)
