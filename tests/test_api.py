from six import string_types
from devicehive import ApiResponseError
from devicehive import DeviceError


def test_get_info(test):

    def handle_connect(handler):
        info = handler.api.get_info()
        assert isinstance(info['api_version'], string_types)
        assert isinstance(info['server_timestamp'], string_types)
        if info.get('rest_server_url'):
            assert info['websocket_server_url'] is None
            assert isinstance(info['rest_server_url'], string_types)
            return
        assert isinstance(info['websocket_server_url'], string_types)
        assert info['rest_server_url'] is None

    test.run(handle_connect)


def test_get_cluster_info(test):

    def handle_connect(handler):
        cluster_info = handler.api.get_cluster_info()
        assert isinstance(cluster_info['bootstrap.servers'], string_types)
        assert isinstance(cluster_info['zookeeper.connect'], string_types)

    test.run(handle_connect)


def test_subscribe_insert_commands(test):

    test.only_websocket_implementation()

    def init_devices(handler):
        test_id = test.generate_id('s-i-c')
        options = [{'id': '%s-1' % test_id}, {'id': '%s-2' % test_id}]
        devices, device_ids, command_ids, command_names = [], [], [], []
        for option in options:
            device = handler.api.put_device(option['id'])
            devices.append(device)
            device_ids.append(device.id)
            command_name = '%s-name' % device.id
            command = device.send_command(command_name)
            command_ids.append(command.id)
            command_names.append(command_name)
        return devices, device_ids, command_ids, command_names

    def set_handler_data(handler, devices, device_ids, command_ids,
                         command_names):
        handler.data['devices'] = devices
        handler.data['device_ids'] = device_ids
        handler.data['command_ids'] = command_ids
        handler.data['command_names'] = command_names

    def handle_connect(handler):
        devices, device_ids, command_ids, command_names = init_devices(handler)
        handler.api.subscribe_insert_commands(device_ids)
        set_handler_data(handler, devices, device_ids, command_ids,
                         command_names)

    def handle_command_insert(handler, command):
        assert command.id in handler.data['command_ids']
        handler.data['command_ids'].remove(command.id)
        if handler.data['command_ids']:
            return
        [device.remove() for device in handler.data['devices']]
        handler.disconnect()

    test.run(handle_connect, handle_command_insert)

    def handle_connect(handler):
        devices, device_ids, command_ids, command_names = init_devices(handler)
        command_name = command_names[0]
        handler.api.subscribe_insert_commands(device_ids, names=[command_name])
        set_handler_data(handler, devices, device_ids, command_ids,
                         command_names)

    def handle_command_insert(handler, command):
        assert command.id == handler.data['command_ids'][0]
        [device.remove() for device in handler.data['devices']]
        handler.disconnect()

    test.run(handle_connect, handle_command_insert)

    def handle_connect(handler):
        devices, device_ids, command_ids, command_names = init_devices(handler)
        handler.api.subscribe_insert_commands(device_ids)
        [device.remove() for device in devices]

    def handle_command_insert(*_):
        assert False

    test.run(handle_connect, handle_command_insert, timeout=5)

    def handle_connect(handler):
        devices, device_ids, command_ids, command_names = init_devices(handler)
        handler.api.subscribe_insert_commands(device_ids)
        try:
            handler.api.subscribe_insert_commands(device_ids)
            assert False
        except DeviceError:
            pass
        [device.remove() for device in devices]
        # TODO: add http support after server response will be fixed.
        if test.http_transport:
            return
        try:
            handler.api.subscribe_insert_commands(device_ids)
            assert False
        except ApiResponseError as api_response_error:
            assert api_response_error.code == 403

    test.run(handle_connect)


def test_list_devices(test):

    def handle_connect(handler):
        test_id = test.generate_id('l-d')
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
        name_pattern = test.generate_id('l-d-n-e')
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


def test_get_device(test):

    def handle_connect(handler):
        device_id = test.generate_id('g-d')
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
        device_id = test.generate_id('g-d-n-e')
        try:
            handler.api.get_device(device_id)
            assert False
        except ApiResponseError as api_response_error:
            # TODO: uncomment after server response will be fixed.
            # assert api_response_error.code() == 404
            pass

    test.run(handle_connect)


def test_put_device(test):

    def handle_connect(handler):
        device_id = test.generate_id('p-d')
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
