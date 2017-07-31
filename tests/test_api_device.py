from devicehive import DeviceError
from devicehive import ApiResponseError


def list_notifications(device, **params):
    notifications = device.list_notifications(**params)
    return [notification for notification in notifications
            if notification.notification[0] != '$']


def test_list(test):

    def handle_connect(handler):
        test_id = test.generate_id('list')
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
        device_id = test.generate_id('get')
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
        device_id = test.generate_id('put')
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
        device_id = test.generate_id('save')
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


def test_list_commands(test):

    def handle_connect(handler):
        server_timestamp = handler.api.get_info()['server_timestamp']
        test_id = test.generate_id('list-commands')
        options = [{'command': '%s-name-1' % test_id, 'lifetime': 100,
                    'status': '1'},
                   {'command': '%s-name-2' % test_id, 'lifetime': 100,
                    'status': '2'}]
        device = handler.api.put_device(test_id)
        for option in options:
            device.send_command(option['command'], lifetime=option['lifetime'],
                                status=option['status'])
        commands = device.list_commands()
        assert len(commands) == len(options)
        commands = device.list_commands(start=server_timestamp)
        assert len(commands) == len(options)
        assert not device.list_commands(start=server_timestamp,
                                        end=server_timestamp)
        command_name = options[0]['command']
        command, = device.list_commands(command=command_name)
        assert command.command == command_name
        status = options[0]['status']
        command, = device.list_commands(status=status)
        assert command.status == status
        command_0, command_1 = device.list_commands(sort_field='command',
                                                    sort_order='ASC')
        assert command_0.command == options[0]['command']
        assert command_1.command == options[1]['command']
        command_0, command_1 = device.list_commands(sort_field='command',
                                                    sort_order='DESC')
        assert command_0.command == options[1]['command']
        assert command_1.command == options[0]['command']
        command, = device.list_commands(sort_field='command', sort_order='ASC',
                                        take=1)
        assert command.command == options[0]['command']
        command, = device.list_commands(sort_field='command', sort_order='ASC',
                                        take=1, skip=1)
        assert command.command == options[1]['command']
        device_1 = handler.api.get_device(test_id)
        device.remove()
        try:
            device.list_commands()
            assert False
        except DeviceError:
            pass
        try:
            device_1.list_commands()
            assert False
        except ApiResponseError as api_response_error:
            # TODO: uncomment after server response will be fixed.
            # assert api_response_error.code() == 404
            pass

    test.run(handle_connect)


def test_send_command(test):

    def handle_connect(handler):
        device_id = test.generate_id('send-command')
        command_name = test.generate_id('send-command')
        device = handler.api.put_device(device_id)
        command = device.send_command(command_name)
        assert command.device_id == device_id
        assert isinstance(command.id, int)
        assert isinstance(command.user_id, int)
        assert command.command == command_name
        assert not command.parameters
        assert not command.lifetime
        assert command.timestamp
        assert command.last_updated
        assert not command.status
        assert not command.result
        command_name = test.generate_id('send-command')
        parameters = {'parameters_key': 'parameters_value'}
        lifetime = 10
        status = 'status'
        result = {'result_key': 'result_value'}
        command = device.send_command(command_name, parameters=parameters,
                                      lifetime=lifetime, status=status,
                                      result=result)
        assert command.device_id == device_id
        assert isinstance(command.id, int)
        assert isinstance(command.user_id, int)
        assert command.command == command_name
        assert command.parameters == parameters
        assert command.lifetime == lifetime
        assert command.timestamp
        assert command.last_updated
        assert command.status == status
        assert command.result == result
        device_1 = handler.api.get_device(device_id)
        device.remove()
        try:
            device.send_command(command_name)
            assert False
        except DeviceError:
            pass
        try:
            device_1.send_command(command_name)
            assert False
        except ApiResponseError as api_response_error:
            # TODO: uncomment after server response will be fixed.
            # assert api_response_error.code() == 404
            pass

    test.run(handle_connect)


def test_list_notifications(test):

    def handle_connect(handler):
        server_timestamp = handler.api.get_info()['server_timestamp']
        test_id = test.generate_id('list-notifications')
        options = [{'notification': '%s-name-1' % test_id,
                    'parameters': {'parameters_key': '1'}},
                   {'notification': '%s-name-2' % test_id,
                    'parameters': {'parameters_key': '2'}}]
        device = handler.api.put_device(test_id)
        for option in options:
            device.send_notification(option['notification'],
                                     parameters=option['parameters'])
        notifications = list_notifications(device)
        assert len(notifications) == len(options)
        notifications = list_notifications(device, start=server_timestamp)
        assert len(notifications) == len(options)
        assert not list_notifications(device, start=server_timestamp,
                                      end=server_timestamp)
        notification_name = options[0]['notification']
        notification, = list_notifications(device,
                                           notification=notification_name)
        assert notification.notification == notification_name
        notification_0, notification_1 = list_notifications(device,
                                                            sort_field=
                                                            'notification',
                                                            sort_order='ASC')
        assert notification_0.notification == options[0]['notification']
        assert notification_1.notification == options[1]['notification']
        notification_0, notification_1 = list_notifications(device,
                                                            sort_field=
                                                            'notification',
                                                            sort_order='DESC')
        assert notification_0.notification == options[1]['notification']
        assert notification_1.notification == options[0]['notification']
        notification_name = test_id
        notification_0 = device.send_notification(notification_name)
        notification_1 = device.send_notification(notification_name)
        notification, = device.list_notifications(notification=
                                                  notification_name,
                                                  sort_field='timestamp',
                                                  sort_order='ASC', take=1)
        assert notification.id == notification_0.id
        notification, = device.list_notifications(notification=
                                                  notification_name,
                                                  sort_field='timestamp',
                                                  sort_order='ASC', take=1,
                                                  skip=1)
        assert notification.id == notification_1.id
        device_1 = handler.api.get_device(test_id)
        device.remove()
        try:
            device.list_notifications()
            assert False
        except DeviceError:
            pass
        try:
            device_1.list_commands()
            assert False
        except ApiResponseError as api_response_error:
            # TODO: uncomment after server response will be fixed.
            # assert api_response_error.code() == 404
            pass

    test.run(handle_connect)


def test_send_notification(test):

    def handle_connect(handler):
        device_id = test.generate_id('send-notification')
        notification_name = test.generate_id('send-notification')
        device = handler.api.put_device(device_id)
        notification = device.send_notification(notification_name)
        assert notification.device_id == device_id
        assert isinstance(notification.id, int)
        assert notification.notification == notification_name
        assert not notification.parameters
        assert notification.timestamp
        parameters = {'parameters_key': 'parameters_value'}
        notification = device.send_notification(notification_name,
                                                parameters=parameters)
        assert notification.device_id == device_id
        assert isinstance(notification.id, int)
        assert notification.notification == notification_name
        assert notification.parameters == parameters
        assert notification.timestamp
        device_1 = handler.api.get_device(device_id)
        device.remove()
        try:
            device.send_notification(notification_name)
            assert False
        except DeviceError:
            pass
        try:
            device_1.send_notification(notification_name)
            assert False
        except ApiResponseError as api_response_error:
            # TODO: uncomment after server response will be fixed.
            # assert api_response_error.code() == 404
            pass

    test.run(handle_connect)
