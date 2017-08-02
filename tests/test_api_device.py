from devicehive import DeviceError
from devicehive import ApiResponseError


def list_notifications(device, **params):
    notifications = device.list_notifications(**params)
    return [notification for notification in notifications
            if notification.notification[0] != '$']


def test_save(test):

    def handle_connect(handler):
        device_id = test.generate_id('d-s')
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
        device_id = test.generate_id('d-r')
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

    def set_handler_data(handler, device, commands, command_ids,
                         subscription_id):
        handler.data['device'] = device
        handler.data['commands'] = commands
        handler.data['command_ids'] = command_ids
        handler.data['subscription_id'] = subscription_id

    def handle_connect(handler):
        device, commands, command_ids = init_device(handler)
        subscription_id = device.subscribe_insert_commands()
        set_handler_data(handler, device, commands, command_ids,
                         subscription_id)

    def handle_command_insert(handler, subscription_id, command):
        assert subscription_id == handler.data['subscription_id']
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
        subscription_id = device.subscribe_insert_commands(names=[command_name])
        set_handler_data(handler, device, commands, command_ids,
                         subscription_id)

    def handle_command_insert(handler, subscription_id, command):
        assert subscription_id == handler.data['subscription_id']
        assert command.id == handler.data['command_ids'][0]
        handler.data['device'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_command_insert)

    def handle_connect(handler):
        device, commands, command_ids = init_device(handler)
        subscription_id = device.subscribe_insert_commands(limit=1)
        set_handler_data(handler, device, commands, command_ids,
                         subscription_id)

    test.run(handle_connect, handle_command_insert)

    def handle_connect(handler):
        device, commands, command_ids = init_device(handler)
        device_1 = handler.api.get_device(device.id)
        device.remove()
        try:
            device.subscribe_insert_commands()
            assert False
        except DeviceError:
            pass
        # TODO: add http support after server response will be fixed.
        if test.http_transport:
            return
        try:
            device_1.subscribe_insert_commands()
            assert False
        except ApiResponseError as api_response_error:
            assert api_response_error.code == 403

    test.run(handle_connect)


def test_unsubscribe_commands(test):

    def handle_connect(handler):
        device_id = test.generate_id('d-u-c')
        command_name = test.generate_id('d-u-c')
        device = handler.api.put_device(device_id)
        device.send_command(command_name)
        insert_subscription_id = device.subscribe_insert_commands()
        # TODO: add device.subscribe_update_commands()
        device.unsubscribe_commands(insert_subscription_id)
        # TODO: add websocket support after server response will be fixed.
        if test.http_transport:
            try:
                device.unsubscribe_commands(insert_subscription_id)
                assert False
            except ApiResponseError as api_response_error:
                assert api_response_error.code == 403
        device_1 = handler.api.get_device(device_id)
        device.remove()
        try:
            device.subscribe_insert_commands()
            assert False
        except DeviceError:
            pass
        # TODO: uncomment after server response will be fixed.
        # try:
        #     device_1.subscribe_insert_commands()
        #     assert False
        # except ApiResponseError as api_response_error:
        #     assert api_response_error.code == 403

    test.run(handle_connect)


def test_list_commands(test):

    def handle_connect(handler):
        server_timestamp = handler.api.get_info()['server_timestamp']
        test_id = test.generate_id('d-l-c')
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
        device_id = test.generate_id('d-s-c')
        command_name = test.generate_id('d-s-c')
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
        test_id = test.generate_id('d-l-n')
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
            # TODO: uncomment after server response will be fixed.
            # assert api_response_error.code() == 404
            pass

    test.run(handle_connect)
