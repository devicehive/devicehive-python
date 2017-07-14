from devicehive.api_object import ApiObjectResponseException


def test_get(test):

    def handle_connect(handler):
        device_id = test.generate_id('get')
        name = '%s-name' % device_id
        data = {'key': 'value'}
        handler.api.put_device(device_id, name=name, data=data)
        device = handler.api.get_device(device_id)
        assert device.id() == device_id
        assert device.name == name
        assert device.data == data
        assert isinstance(device.network_id, int)
        assert not device.is_blocked
        device.remove()

    test.run(handle_connect)


def test_get_not_exist(test):

    def handle_connect(handler):
        device_id = test.generate_id('get-not-exist')
        try:
            handler.api.get_device(device_id)
            assert False
        except ApiObjectResponseException as api_object_response_exception:
            # TODO: test for 404 for all transports after bug will be fixed.
            if test.websocket_transport():
                assert api_object_response_exception.code() == 404
            if test.http_transport():
                assert api_object_response_exception.code() == 401

    test.run(handle_connect)
