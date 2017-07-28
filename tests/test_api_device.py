from devicehive import DeviceError
from devicehive import ApiResponseError


def test_list(test):

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


def test_get(test):

    def handle_connect(handler):
        device_id = test.generate_id('get-device')
        name = '%s-name' % device_id
        data = {'data_key': 'data_value'}
        handler.api.put_device(device_id, name=name, data=data)
        device = handler.api.get_device(device_id)
        assert device.id == device_id
        assert device.name == name
        assert device.data == data
        assert isinstance(device.network_id, int)
        assert not device.is_blocked
        device.remove()
        device_id = test.generate_id('get-device-not-exist')
        try:
            handler.api.get_device(device_id)
            assert False
        except ApiResponseError as api_response_error:
            # TODO: uncomment after server response will be fixed.
            # assert api_response_error.code() == 404
            pass

    test.run(handle_connect)


def test_put(test):

    def handle_connect(handler):
        device_id = test.generate_id('put-device')
        device = handler.api.put_device(device_id)
        assert device.id == device_id
        assert device.name == device_id
        assert not device.data
        assert isinstance(device.network_id, int)
        assert not device.is_blocked
        device.remove()
        name = '%s-name' % device_id
        data = {'data_key': 'data_value'}
        device = handler.api.put_device(device_id, name=name, data=data,
                                        is_blocked=True)
        assert device.id == device_id
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
        data = {'data_key': 'data_value'}
        device.name = name
        device.data = data
        device.is_blocked = True
        device.save()
        device = handler.api.get_device(device_id)
        assert device.id == device_id
        assert device.name == name
        assert device.data == data
        assert isinstance(device.network_id, int)
        assert device.is_blocked
        device.remove()
        try:
            device.save()
            assert False
        except DeviceError:
            pass

    test.run(handle_connect)


def test_remove(test):

    def handle_connect(handler):
        device_id = test.generate_id('remove-device')
        device = handler.api.put_device(device_id)
        device.remove()
        assert not device.id
        assert not device.name
        assert not device.data
        assert not device.network_id
        assert not device.is_blocked
        device = handler.api.put_device(device_id)
        device_1 = handler.api.get_device(device_id)
        device.remove()
        try:
            device.remove()
            assert False
        except DeviceError:
            pass
        try:
            device_1.remove()
            assert False
        except ApiResponseError as api_response_error:
            # TODO: uncomment after server response will be fixed.
            # assert api_response_error.code() == 404
            pass

    test.run(handle_connect)
