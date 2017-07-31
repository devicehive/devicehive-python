def test_list_devices(test):

    def handle_connect(handler):
        test_id = test.generate_id('list-devices')
        options = [{'id': '%s-1' % test_id, 'name': '%s-name-1' % test_id},
                   {'id': '%s-2' % test_id, 'name': '%s-name-2' % test_id}]
        test_devices = [handler.api.put_device(option['id'],
                                               name=option['name'])
                        for option in options]
        devices = handler.api.list_devices()
        assert len(devices) >= len(options)
        name = options[0]['name']
        device, = handler.api.list_devices(name=name)
        assert device.name == name
        name_pattern = test.generate_id('list-not-exist')
        assert not handler.api.list_devices(name_pattern=name_pattern)
        name_pattern = test_id + '%'
        devices = handler.api.list_devices(name_pattern=name_pattern)
        assert len(devices) == len(options)
        device_0, device_1 = handler.api.list_devices(name_pattern=name_pattern,
                                                      sort_field='name',
                                                      sort_order='ASC')
        assert device_0.id == options[0]['id']
        assert device_1.id == options[1]['id']
        device_0, device_1 = handler.api.list_devices(name_pattern=name_pattern,
                                                      sort_field='name',
                                                      sort_order='DESC')
        assert device_0.id == options[1]['id']
        assert device_1.id == options[0]['id']
        device, = handler.api.list_devices(name_pattern=name_pattern,
                                           sort_field='name', sort_order='ASC',
                                           take=1)
        assert device.id == options[0]['id']
        device, = handler.api.list_devices(name_pattern=name_pattern,
                                           sort_field='name', sort_order='ASC',
                                           take=1, skip=1)
        assert device.id == options[1]['id']
        for test_device in test_devices:
            test_device.remove()

    test.run(handle_connect)
