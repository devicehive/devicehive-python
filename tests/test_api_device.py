from devicehive import DeviceError
from devicehive import ApiResponseError


def test_save(test):
    device_hive_api = test.device_hive_api()
    device_id = test.generate_id('d-s')
    device = device_hive_api.put_device(device_id)
    name = '%s-name' % device_id
    data = {'data_key': 'data_value'}
    device.name = name
    device.data = data
    device.is_blocked = True
    device.save()
    device = device_hive_api.get_device(device_id)
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


def test_remove(test):
    device_hive_api = test.device_hive_api()
    device_id = test.generate_id('d-r')
    device = device_hive_api.put_device(device_id)
    device_1 = device_hive_api.get_device(device_id)
    device.remove()
    assert not device.id
    assert not device.name
    assert not device.data
    assert not device.network_id
    assert not device.is_blocked
    try:
        device.remove()
        assert False
    except DeviceError:
        pass
    try:
        device_1.remove()
        assert False
    except ApiResponseError as api_response_error:
        if test.admin_refresh_token:
            assert api_response_error.code == 404
        else:
            assert api_response_error.code == 403


def test_subscribe_insert_commands(test):

    def init_device(handler):
        test_id = test.generate_id('d-s-i-c')
        options = [{'command': '%s-name-1' % test_id},
                   {'command': '%s-name-2' % test_id}]
        device = handler.api.put_device(test_id)
        commands, command_ids = [], []
        for option in options:
            command = device.send_command(option['command'])
            commands.append(command)
            command_ids.append(command.id)
        return device, commands, command_ids

    def set_handler_data(handler, device, commands, command_ids):
        handler.data['device'] = device
        handler.data['commands'] = commands
        handler.data['command_ids'] = command_ids

    def handle_connect(handler):
        device, commands, command_ids = init_device(handler)
        device.subscribe_insert_commands()
        set_handler_data(handler, device, commands, command_ids)

    def handle_command_insert(handler, command):
        assert command.id in handler.data['command_ids']
        handler.data['command_ids'].remove(command.id)
        if handler.data['command_ids']:
            return
        handler.data['device'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_command_insert)

    def handle_connect(handler):
        device, commands, command_ids = init_device(handler)
        command_name = commands[0].command
        device.subscribe_insert_commands(names=[command_name])
        set_handler_data(handler, device, commands, command_ids)

    def handle_command_insert(handler, command):
        assert command.id == handler.data['command_ids'][0]
        handler.data['device'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_command_insert)

    def handle_connect(handler):
        device, commands, command_ids = init_device(handler)
        device.subscribe_insert_commands()
        try:
            device.subscribe_insert_commands()
            assert False
        except DeviceError:
            pass
        device_1 = handler.api.get_device(device.id)
        device.remove()
        try:
            device.subscribe_insert_commands()
            assert False
        except DeviceError:
            pass
        if test.http_transport:
            return
        try:
            device_1.subscribe_insert_commands()
            assert False
        except ApiResponseError as api_response_error:
            if test.admin_refresh_token:
                assert api_response_error.code == 404
            else:
                assert api_response_error.code == 403

    test.run(handle_connect)


def test_unsubscribe_insert_commands(test):

    def handle_connect(handler):
        device_id = test.generate_id('d-u-i-c')
        device = handler.api.put_device(device_id)
        device.subscribe_insert_commands()
        device.unsubscribe_insert_commands()
        try:
            device.unsubscribe_insert_commands()
            assert False
        except DeviceError:
            pass
        device_1 = handler.api.get_device(device.id)
        device_1.subscribe_insert_commands()
        device.remove()
        try:
            device.unsubscribe_insert_commands()
            assert False
        except DeviceError:
            pass

    test.run(handle_connect)


def test_subscribe_update_commands(test):

    def init_device(handler):
        test_id = test.generate_id('d-s-u-c')
        options = [{'command': '%s-name-1' % test_id},
                   {'command': '%s-name-2' % test_id}]
        device = handler.api.put_device(test_id)
        commands, command_ids = [], []
        for option in options:
            command = device.send_command(option['command'])
            command.status = 'status'
            command.save()
            commands.append(command)
            command_ids.append(command.id)
        return device, commands, command_ids

    def set_handler_data(handler, device, commands, command_ids):
        handler.data['device'] = device
        handler.data['commands'] = commands
        handler.data['command_ids'] = command_ids

    def handle_connect(handler):
        device, commands, command_ids = init_device(handler)
        device.subscribe_update_commands()
        set_handler_data(handler, device, commands, command_ids)

    def handle_command_update(handler, command):
        assert command.id in handler.data['command_ids']
        handler.data['command_ids'].remove(command.id)
        if handler.data['command_ids']:
            return
        handler.data['device'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_command_update=handle_command_update)

    def handle_connect(handler):
        device, commands, command_ids = init_device(handler)
        command_name = commands[0].command
        device.subscribe_update_commands(names=[command_name])
        set_handler_data(handler, device, commands, command_ids)

    def handle_command_update(handler, command):
        assert command.id == handler.data['command_ids'][0]
        handler.data['device'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_command_update=handle_command_update)

    def handle_connect(handler):
        device, commands, command_ids = init_device(handler)
        device.subscribe_update_commands()
        try:
            device.subscribe_update_commands()
            assert False
        except DeviceError:
            pass
        device_1 = handler.api.get_device(device.id)
        device.remove()
        try:
            device.subscribe_update_commands()
            assert False
        except DeviceError:
            pass
        if test.http_transport:
            return
        try:
            device_1.subscribe_update_commands()
            assert False
        except ApiResponseError as api_response_error:
            if test.admin_refresh_token:
                assert api_response_error.code == 404
            else:
                assert api_response_error.code == 403

    test.run(handle_connect)


def test_unsubscribe_update_commands(test):

    def handle_connect(handler):
        device_id = test.generate_id('d-u-u-c')
        device = handler.api.put_device(device_id)
        device.subscribe_update_commands()
        device.unsubscribe_update_commands()
        try:
            device.unsubscribe_update_commands()
            assert False
        except DeviceError:
            pass
        device_1 = handler.api.get_device(device.id)
        device_1.subscribe_update_commands()
        device.remove()
        try:
            device.unsubscribe_update_commands()
            assert False
        except DeviceError:
            pass

    test.run(handle_connect)


def test_list_commands(test):
    device_hive_api = test.device_hive_api()
    server_timestamp = device_hive_api.get_info()['server_timestamp']
    test_id = test.generate_id('d-l-c')
    options = [{'command': '%s-name-1' % test_id, 'lifetime': 100,
                'status': '1'},
               {'command': '%s-name-2' % test_id, 'lifetime': 100,
                'status': '2'}]
    device = device_hive_api.put_device(test_id)
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
    device_1 = device_hive_api.get_device(test_id)
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
        if test.admin_refresh_token:
            assert api_response_error.code == 404
        else:
            assert api_response_error.code == 403


def test_send_command(test):
    device_hive_api = test.device_hive_api()
    device_id = test.generate_id('d-s-c')
    command_name = test.generate_id('d-s-c')
    device = device_hive_api.put_device(device_id)
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
    command_name = test.generate_id('d-s-c')
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
    device_1 = device_hive_api.get_device(device_id)
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
        if test.admin_refresh_token:
            assert api_response_error.code == 404
        # TODO: finish after fix.
        # else:
        #     assert api_response_error.code == 403


def test_subscribe_notifications(test):

    def init_device(handler):
        test_id = test.generate_id('d-s-n')
        options = [{'notification': '%s-name-1' % test_id},
                   {'notification': '%s-name-2' % test_id}]
        device = handler.api.put_device(test_id)
        notifications, notification_ids = [], []
        for option in options:
            notification = device.send_notification(option['notification'])
            notifications.append(notification)
            notification_ids.append(notification.id)
        return device, notifications, notification_ids

    def set_handler_data(handler, device, notifications, notification_ids):
        handler.data['device'] = device
        handler.data['notifications'] = notifications
        handler.data['notification_ids'] = notification_ids

    def handle_connect(handler):
        device, notifications, notification_ids = init_device(handler)
        device.subscribe_notifications()
        set_handler_data(handler, device, notifications, notification_ids)

    def handle_notification(handler, notification):
        if notification.notification[0] == '$':
            return
        assert notification.id in handler.data['notification_ids']
        handler.data['notification_ids'].remove(notification.id)
        if handler.data['notification_ids']:
            return
        handler.data['device'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_notification=handle_notification)

    def handle_connect(handler):
        device, notifications, notification_ids = init_device(handler)
        notification_name = notifications[0].notification
        device.subscribe_notifications(names=[notification_name])
        set_handler_data(handler, device, notifications, notification_ids)

    def handle_notification(handler, notification):
        assert notification.id == handler.data['notification_ids'][0]
        handler.data['device'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_notification=handle_notification)

    def handle_connect(handler):
        device, notifications, notification_ids = init_device(handler)
        device.subscribe_notifications()
        try:
            device.subscribe_notifications()
            assert False
        except DeviceError:
            pass
        device_1 = handler.api.get_device(device.id)
        device.remove()
        try:
            device.subscribe_notifications()
            assert False
        except DeviceError:
            pass
        if test.http_transport:
            return
        try:
            device_1.subscribe_notifications()
            assert False
        except ApiResponseError as api_response_error:
            if test.admin_refresh_token:
                assert api_response_error.code == 404
            else:
                assert api_response_error.code == 403

    test.run(handle_connect)


def test_unsubscribe_notifications(test):

    def handle_connect(handler):
        device_id = test.generate_id('d-u-n')
        device = handler.api.put_device(device_id)
        device.subscribe_notifications()
        device.unsubscribe_notifications()
        try:
            device.unsubscribe_notifications()
            assert False
        except DeviceError:
            pass
        device_1 = handler.api.get_device(device.id)
        device_1.subscribe_notifications()
        device.remove()
        try:
            device.unsubscribe_notifications()
            assert False
        except DeviceError:
            pass

    test.run(handle_connect)


def list_notifications(device, **params):
    notifications = device.list_notifications(**params)
    return [notification for notification in notifications
            if notification.notification[0] != '$']


def test_list_notifications(test):
    device_hive_api = test.device_hive_api()
    server_timestamp = device_hive_api.get_info()['server_timestamp']
    test_id = test.generate_id('d-l-n')
    options = [{'notification': '%s-name-1' % test_id,
                'parameters': {'parameters_key': '1'}},
               {'notification': '%s-name-2' % test_id,
                'parameters': {'parameters_key': '2'}}]
    device = device_hive_api.put_device(test_id)
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
    notification_0, notification_1 = list_notifications(
        device, sort_field='notification', sort_order='ASC')
    assert notification_0.notification == options[0]['notification']
    assert notification_1.notification == options[1]['notification']
    notification_0, notification_1 = list_notifications(
        device, sort_field='notification', sort_order='DESC')
    assert notification_0.notification == options[1]['notification']
    assert notification_1.notification == options[0]['notification']
    notification_name = test_id
    notification_0 = device.send_notification(notification_name)
    notification_1 = device.send_notification(notification_name)
    notification, = device.list_notifications(
        notification=notification_name, sort_field='timestamp',
        sort_order='ASC', take=1)
    assert notification.id == notification_0.id
    notification, = device.list_notifications(
        notification=notification_name, sort_field='timestamp',
        sort_order='ASC', take=1, skip=1)
    assert notification.id == notification_1.id
    device_1 = device_hive_api.get_device(test_id)
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
        if test.admin_refresh_token:
            assert api_response_error.code == 404
        else:
            assert api_response_error.code == 403


def test_send_notification(test):

    def handle_connect(handler):
        device_id = test.generate_id('d-s-n')
        notification_name = test.generate_id('d-s-n')
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
            if test.admin_refresh_token:
                assert api_response_error.code == 404
            else:
                assert api_response_error.code == 403

    test.run(handle_connect)
