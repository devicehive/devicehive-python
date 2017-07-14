from devicehive.api_object import ApiObjectResponseException


def test_list(test):

    def handle_connect(handler):
        test_id = test.generate_id('list')
        device_options = [{'id': '%s-1' % test_id,
                          'name': '%s-name-1' % test_id},
                          {'id': '%s-2' % test_id,
                           'name': '%s-name-2' % test_id}]
        devices = [handler.api.put_device(device_option['id'],
                                          device_option['name'])
                   for device_option in device_options]
        devices_list = handler.api.list_devices()
        assert devices_list[0].id() == device_options[1]['id']
        assert devices_list[1].id() == device_options[0]['id']
        name = device_options[0]['name']
        devices_list = handler.api.list_devices(name=name)
        assert len(devices_list) == 1
        assert devices_list[0].name == name
        name_pattern = test.generate_id('list-not-exist')
        devices_list = handler.api.list_devices(name_pattern=name_pattern)
        assert not devices_list
        name_pattern = test_id + '%'
        devices_list = handler.api.list_devices(name_pattern=name_pattern)
        assert len(devices_list) == 2
        devices_list = handler.api.list_devices(name_pattern=name_pattern,
                                                sort_field='name',
                                                sort_order='ASC')
        assert devices_list[0].id() == device_options[0]['id']
        assert devices_list[1].id() == device_options[1]['id']
        devices_list = handler.api.list_devices(name_pattern=name_pattern,
                                                sort_field='name',
                                                sort_order='DESC')
        assert devices_list[0].id() == device_options[1]['id']
        assert devices_list[1].id() == device_options[0]['id']
        devices_list = handler.api.list_devices(name_pattern=name_pattern,
                                                sort_field='name',
                                                sort_order='ASC',
                                                take=1)
        assert len(devices_list) == 1
        devices_list = handler.api.list_devices(name_pattern=name_pattern,
                                                sort_field='name',
                                                sort_order='ASC',
                                                take=1, skip=1)
        assert devices_list[0].id() == device_options[1]['id']
        assert len(devices_list) == 1
        for device in devices:
            device.remove()

    test.run(handle_connect)


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
