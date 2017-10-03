from six import string_types
from devicehive import ApiResponseError
from devicehive import DeviceError
from devicehive.user import User


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


def test_create_token(test):

    def handle_connect(handler):
        login = test.generate_id('c-t')
        password = test.generate_id('c-t')
        role = User.ADMINISTRATOR_ROLE
        data = {'k': 'v'}
        user = handler.api.create_user(login, password, role, data)
        tokens = handler.api.create_token(user.id)
        assert isinstance(tokens['access_token'], string_types)
        assert isinstance(tokens['refresh_token'], string_types)
        user_id = user.id
        user.remove()
        try:
            handler.api.create_token(user_id)
            assert False
        except ApiResponseError as api_response_error:
            assert api_response_error.code == 404

    test.only_admin_implementation()
    test.run(handle_connect)


def test_refresh_token(test):

    def handle_connect(handler):
        access_token = handler.api.refresh_token()
        assert isinstance(access_token, string_types)

    test.run(handle_connect)


def test_subscribe_insert_commands(test):

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
        try:
            handler.api.subscribe_insert_commands(device_ids)
            assert False
        except DeviceError:
            pass
        [device.remove() for device in devices]
        if test.http_transport:
            return
        try:
            handler.api.subscribe_insert_commands(device_ids)
            assert False
        except ApiResponseError as api_response_error:
            assert api_response_error.code == 404

    test.run(handle_connect)


def test_unsubscribe_insert_commands(test):

    def handle_connect(handler):
        test_id = test.generate_id('u-i-c')
        device_ids = ['%s-1' % test_id, '%s-2' % test_id, '%s-3' % test_id]
        devices = []
        for device_id in device_ids:
            device = handler.api.put_device(device_id)
            devices.append(device)
            command_name = '%s-name' % device_id
            device.send_command(command_name)
        handler.api.subscribe_insert_commands(device_ids)
        handler.api.unsubscribe_insert_commands(device_ids)
        try:
            handler.api.unsubscribe_insert_commands(device_ids)
            assert False
        except DeviceError:
            pass
        handler.api.subscribe_insert_commands(device_ids)
        [device.remove() for device in devices]
        try:
            handler.api.unsubscribe_insert_commands(device_ids)
            assert False
        except DeviceError:
            pass

    test.run(handle_connect)


def test_subscribe_update_commands(test):

    def init_devices(handler):
        test_id = test.generate_id('s-u-c')
        options = [{'id': '%s-1' % test_id}, {'id': '%s-2' % test_id}]
        devices, device_ids, command_ids, command_names = [], [], [], []
        for option in options:
            device = handler.api.put_device(option['id'])
            devices.append(device)
            device_ids.append(device.id)
            command_name = '%s-name' % device.id
            command = device.send_command(command_name)
            command.status = 'status'
            command.save()
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
        handler.api.subscribe_update_commands(device_ids)
        set_handler_data(handler, devices, device_ids, command_ids,
                         command_names)

    def handle_command_update(handler, command):
        assert command.id in handler.data['command_ids']
        handler.data['command_ids'].remove(command.id)
        if handler.data['command_ids']:
            return
        [device.remove() for device in handler.data['devices']]
        handler.disconnect()

    test.run(handle_connect, handle_command_update=handle_command_update)

    def handle_connect(handler):
        devices, device_ids, command_ids, command_names = init_devices(handler)
        command_name = command_names[0]
        handler.api.subscribe_update_commands(device_ids, names=[command_name])
        set_handler_data(handler, devices, device_ids, command_ids,
                         command_names)

    def handle_command_update(handler, command):
        assert command.id == handler.data['command_ids'][0]
        [device.remove() for device in handler.data['devices']]
        handler.disconnect()

    test.run(handle_connect, handle_command_update=handle_command_update)

    def handle_connect(handler):
        devices, device_ids, command_ids, command_names = init_devices(handler)
        handler.api.subscribe_update_commands(device_ids)
        try:
            handler.api.subscribe_update_commands(device_ids)
            assert False
        except DeviceError:
            pass
        [device.remove() for device in devices]
        if test.http_transport:
            return
        try:
            handler.api.subscribe_update_commands(device_ids)
            assert False
        except ApiResponseError as api_response_error:
            assert api_response_error.code == 404

    test.run(handle_connect)


def test_unsubscribe_update_commands(test):

    def handle_connect(handler):
        test_id = test.generate_id('u-u-c')
        device_ids = ['%s-1' % test_id, '%s-2' % test_id, '%s-3' % test_id]
        devices = []
        for device_id in device_ids:
            device = handler.api.put_device(device_id)
            devices.append(device)
            command_name = '%s-name' % device_id
            command = device.send_command(command_name)
            command.status = 'status'
            command.save()
        handler.api.subscribe_update_commands(device_ids)
        handler.api.unsubscribe_update_commands(device_ids)
        try:
            handler.api.unsubscribe_update_commands(device_ids)
            assert False
        except DeviceError:
            pass
        handler.api.subscribe_update_commands(device_ids)
        [device.remove() for device in devices]
        try:
            handler.api.unsubscribe_update_commands(device_ids)
            assert False
        except DeviceError:
            pass

    test.run(handle_connect)


def test_subscribe_notifications(test):

    def init_devices(handler):
        test_id = test.generate_id('s-n')
        options = [{'id': '%s-1' % test_id}, {'id': '%s-2' % test_id}]
        devices, device_ids, notification_ids = [], [], []
        notification_names = []
        for option in options:
            device = handler.api.put_device(option['id'])
            devices.append(device)
            device_ids.append(device.id)
            notification_name = '%s-name' % device.id
            notification = device.send_notification(notification_name)
            notification_ids.append(notification.id)
            notification_names.append(notification_name)
        return devices, device_ids, notification_ids, notification_names

    def set_handler_data(handler, devices, device_ids, notification_ids,
                         notification_names):
        handler.data['devices'] = devices
        handler.data['device_ids'] = device_ids
        handler.data['notification_ids'] = notification_ids
        handler.data['notification_names'] = notification_names

    def handle_connect(handler):
        (devices,
         device_ids,
         notification_ids,
         notification_names) = init_devices(handler)
        handler.api.subscribe_notifications(device_ids)
        set_handler_data(handler, devices, device_ids, notification_ids,
                         notification_names)

    def handle_notification(handler, notification):
        if notification.notification[0] == '$':
            return
        assert notification.id in handler.data['notification_ids']
        handler.data['notification_ids'].remove(notification.id)
        if handler.data['notification_ids']:
            return
        [device.remove() for device in handler.data['devices']]
        handler.disconnect()

    test.run(handle_connect, handle_notification=handle_notification)

    def handle_connect(handler):
        (devices,
         device_ids,
         notification_ids,
         notification_names) = init_devices(handler)
        notification_name = notification_names[0]
        handler.api.subscribe_notifications(device_ids,
                                            names=[notification_name])
        set_handler_data(handler, devices, device_ids, notification_ids,
                         notification_names)

    def handle_notification(handler, notification):
        assert notification.id == handler.data['notification_ids'][0]
        [device.remove() for device in handler.data['devices']]
        handler.disconnect()

    test.run(handle_connect, handle_notification=handle_notification)

    def handle_connect(handler):
        (devices,
         device_ids,
         notification_ids,
         notification_names) = init_devices(handler)
        handler.api.subscribe_notifications(device_ids)
        try:
            handler.api.subscribe_notifications(device_ids)
            assert False
        except DeviceError:
            pass
        [device.remove() for device in devices]
        if test.http_transport:
            return
        try:
            handler.api.subscribe_notifications(device_ids)
            assert False
        except ApiResponseError as api_response_error:
            assert api_response_error.code == 404

    test.run(handle_connect)


def test_unsubscribe_notifications(test):

    def handle_connect(handler):
        test_id = test.generate_id('u-n')
        device_ids = ['%s-1' % test_id, '%s-2' % test_id, '%s-3' % test_id]
        devices = []
        for device_id in device_ids:
            device = handler.api.put_device(device_id)
            devices.append(device)
            notification_name = '%s-name' % device_id
            device.send_notification(notification_name)
        handler.api.subscribe_notifications(device_ids)
        handler.api.unsubscribe_notifications(device_ids)
        try:
            handler.api.unsubscribe_notifications(device_ids)
            assert False
        except DeviceError:
            pass
        handler.api.subscribe_notifications(device_ids)
        [device.remove() for device in devices]
        try:
            handler.api.unsubscribe_notifications(device_ids)
            assert False
        except DeviceError:
            pass

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
        [test_device.remove() for test_device in test_devices]

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
            if test.admin_refresh_token:
                assert api_response_error.code == 404
            # TODO: uncomment after server response for ws for user token will
            # be fixed
            # else:
            #     assert api_response_error.code == 403

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


def test_list_networks(test):

    def handle_connect(handler):
        test_id = test.generate_id('l-n')
        options = [{'name': '%s-name-1' % test_id,
                    'description': '%s-description-1' % test_id},
                   {'name': '%s-name-2' % test_id,
                    'description': '%s-description-2' % test_id}]
        test_networks = [handler.api.create_network(option['name'],
                                                    option['description'])
                         for option in options]
        networks = handler.api.list_networks()
        assert len(networks) >= len(options)
        name = options[0]['name']
        network, = handler.api.list_networks(name=name)
        assert network.name == name
        name_pattern = test.generate_id('l-n-n-e')
        assert not handler.api.list_networks(name_pattern=name_pattern)
        name_pattern = test_id + '%'
        networks = handler.api.list_networks(name_pattern=name_pattern)
        assert len(networks) == len(options)
        network_0, network_1 = handler.api.list_networks(
            name_pattern=name_pattern, sort_field='name', sort_order='ASC')
        assert network_0.name == options[0]['name']
        assert network_1.name == options[1]['name']
        network_0, network_1 = handler.api.list_networks(
            name_pattern=name_pattern, sort_field='name', sort_order='DESC')
        assert network_0.name == options[1]['name']
        assert network_1.name == options[0]['name']
        network, = handler.api.list_networks(name_pattern=name_pattern,
                                             sort_field='name',
                                             sort_order='ASC', take=1)
        assert network.name == options[0]['name']
        network, = handler.api.list_networks(name_pattern=name_pattern,
                                             sort_field='name',
                                             sort_order='ASC', take=1,
                                             skip=1)
        assert network.name == options[1]['name']
        [test_network.remove() for test_network in test_networks]

    test.only_admin_implementation()
    test.run(handle_connect)


def test_get_network(test):

    def handle_connect(handler):
        name = test.generate_id('g-n')
        description = '%s-description' % name
        network = handler.api.create_network(name, description)
        network = handler.api.get_network(network.id)
        assert isinstance(network.id, int)
        assert network.name == name
        assert network.description == description
        network_id = network.id
        network.remove()
        try:
            handler.api.get_network(network_id)
            assert False
        except ApiResponseError as api_response_error:
            assert api_response_error.code == 404

    test.only_admin_implementation()
    test.run(handle_connect)


def test_create_network(test):

    def handle_connect(handler):
        name = test.generate_id('c-n')
        description = '%s-description' % name
        network = handler.api.create_network(name, description)
        assert isinstance(network.id, int)
        assert network.name == name
        assert network.description == description
        try:
            handler.api.create_network(name, description)
            assert False
        except ApiResponseError as api_response_error:
            assert api_response_error.code == 403
        network.remove()

    test.only_admin_implementation()
    test.run(handle_connect)


def test_list_users(test):

    def handle_connect(handler):
        test_id = test.generate_id('l-u')
        role = User.ADMINISTRATOR_ROLE
        options = [{'login': '%s-login-1' % test_id,
                    'password': '%s-password-1' % test_id,
                    'role': role, 'data': {'1': '1'}},
                   {'login': '%s-login-2' % test_id,
                    'password': '%s-password-1' % test_id,
                    'role': role, 'data': {'2': '2'}}]
        test_users = [handler.api.create_user(option['login'],
                                              option['password'],
                                              option['role'],
                                              option['data'])
                      for option in options]
        users = handler.api.list_users()
        assert len(users) >= len(options)
        login = options[0]['login']
        user, = handler.api.list_users(login=login)
        assert user.login == login
        login_pattern = test.generate_id('l-u-n-e')
        assert not handler.api.list_users(login_pattern=login_pattern)
        login_pattern = test_id + '%'
        users = handler.api.list_users(login_pattern=login_pattern)
        assert len(users) == len(options)
        users = handler.api.list_users(role=role)
        assert len(users) >= len(options)
        status = User.ACTIVE_STATUS
        users = handler.api.list_users(status=status)
        assert len(users) >= len(options)
        user_0, user_1 = handler.api.list_users(login_pattern=login_pattern,
                                                sort_field='login',
                                                sort_order='ASC')
        assert user_0.login == options[0]['login']
        assert user_1.login == options[1]['login']
        user_0, user_1 = handler.api.list_users(login_pattern=login_pattern,
                                                sort_field='login',
                                                sort_order='DESC')
        assert user_0.login == options[1]['login']
        assert user_1.login == options[0]['login']
        user, = handler.api.list_users(login_pattern=login_pattern,
                                       sort_field='login', sort_order='ASC',
                                       take=1)
        assert user.login == options[0]['login']
        user, = handler.api.list_users(login_pattern=login_pattern,
                                       sort_field='login', sort_order='ASC',
                                       take=1, skip=1)
        assert user.login == options[1]['login']
        [test_user.remove() for test_user in test_users]

    test.only_admin_implementation()
    test.run(handle_connect)


def test_get_current_user(test):

    def handle_connect(handler):
        user = handler.api.get_current_user()
        assert isinstance(user.id, int)

    test.run(handle_connect)


def test_get_user(test):

    def handle_connect(handler):
        login = test.generate_id('g-u')
        password = test.generate_id('g-u')
        role = User.ADMINISTRATOR_ROLE
        data = {'k': 'v'}
        user = handler.api.create_user(login, password, role, data)
        user = handler.api.get_user(user.id)
        assert isinstance(user.id, int)
        assert user.login == login
        assert not user.last_login
        assert not user.intro_reviewed
        assert user.role == role
        assert user.status == User.ACTIVE_STATUS
        assert user.data == data
        user_id = user.id
        user.remove()
        try:
            handler.api.get_user(user_id)
            assert False
        except ApiResponseError as api_response_error:
            assert api_response_error.code == 404

    test.only_admin_implementation()
    test.run(handle_connect)


def test_create_user(test):

    def handle_connect(handler):
        login = test.generate_id('c-u')
        password = test.generate_id('c-u')
        role = User.ADMINISTRATOR_ROLE
        data = {'k': 'v'}
        user = handler.api.create_user(login, password, role, data)
        assert isinstance(user.id, int)
        assert user.login == login
        assert not user.last_login
        assert not user.intro_reviewed
        assert user.role == role
        assert user.status == User.ACTIVE_STATUS
        assert user.data == data
        try:
            handler.api.create_user(login, password, role, data)
            assert False
        except ApiResponseError as api_response_error:
            assert api_response_error.code == 403
        user.remove()

    test.only_admin_implementation()
    test.run(handle_connect)
