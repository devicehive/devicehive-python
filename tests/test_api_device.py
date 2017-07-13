def test_get(test):

    def handle_connect(handler):
        device_id = 'test-api-get-device-id-%s' % test.transport_name()
        name = 'test-api-get-device-name-%s' % test.transport_name()
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

