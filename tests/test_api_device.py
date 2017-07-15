from devicehive.api_object import ApiObjectResponseException


def test_get(test):

    def handle_connect(handler):
        device_id = test.generate_id('get-device')
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
        device_id = test.generate_id('get-device-not-exist')
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


def test_put(test):

    def handle_connect(handler):
        device_id = test.generate_id('put-device')
        device = handler.api.put_device(device_id)
        assert device.id() == device_id
        assert device.name == device_id
        assert not device.data
        assert isinstance(device.network_id, int)
        assert not device.is_blocked
        device.remove()
        name = '%s-name' % device_id
        data = {'key': 'value'}
        device = handler.api.put_device(device_id, name=name, data=data,
                                        is_blocked=True)
        assert device.id() == device_id
        assert device.name == name
        assert device.data == data
        assert isinstance(device.network_id, int)
        assert device.is_blocked
        device.remove()

    test.run(handle_connect)


def test_save(test):

    def handle_connect(handler):
        device_id = test.generate_id('save-device')
        device = handler.api.put_device(device_id)
        name = '%s-name' % device_id
        data = {'key': 'value'}
        device.name = name
        device.data = data
        device.is_blocked = True
        device.save()
        device = handler.api.get_device(device_id)
        assert device.id() == device_id
        assert device.name == name
        assert device.data == data
        assert isinstance(device.network_id, int)
        assert device.is_blocked
        device.remove()

    test.run(handle_connect)
