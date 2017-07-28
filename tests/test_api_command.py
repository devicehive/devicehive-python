from devicehive import DeviceError
from devicehive import ApiResponseError


def test_list(test):

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


def test_send(test):

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


def test_save(test):

    def handle_connect(handler):
        device_id = test.generate_id('save-command')
        command_name = test.generate_id('save-command')
        device = handler.api.put_device(device_id)
        command = device.send_command(command_name)
        status = 'status'
        result = {'result_key': 'result_value'}
        command.status = status
        command.result = result
        command.save()
        device.remove()
        try:
            command.save()
            assert False
        except ApiResponseError as api_response_error:
            # TODO: uncomment after server response will be fixed.
            # assert api_response_error.code() == 404
            pass

    test.run(handle_connect)
