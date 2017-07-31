from devicehive import DeviceError
from devicehive import ApiResponseError


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
