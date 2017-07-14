def test_list(test):

    def handle_connect(handler):
        test_id = test.generate_id('list-devices')
        device_options = [{'id': '%s-1' % test_id,
                          'name': '%s-name-1' % test_id},
                          {'id': '%s-2' % test_id,
                           'name': '%s-name-2' % test_id}]
        devices = [handler.api.put_device(device_option['id'],
                                          device_option['name'])
                   for device_option in device_options]
        devices_list = handler.api.list_devices()
        assert len(devices_list) >= len(device_options)
        name = device_options[0]['name']
        devices_list = handler.api.list_devices(name=name)
        assert len(devices_list) == 1
        assert devices_list[0].name == name
        name_pattern = test.generate_id('list-not-exist')
        devices_list = handler.api.list_devices(name_pattern=name_pattern)
        assert not devices_list
        name_pattern = test_id + '%'
        devices_list = handler.api.list_devices(name_pattern=name_pattern)
        assert len(devices_list) == len(device_options)
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
