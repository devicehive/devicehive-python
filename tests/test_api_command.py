from tests import string
from devicehive import DeviceException
from devicehive import ApiResponseException


def test_send(test):

    def handle_connect(handler):
        device_id = test.generate_id('send-command')
        command_name = test.generate_id('send-command')
        device = handler.api.put_device(device_id)
        command = device.send_command(command_name)
        assert command.device_id() == device_id
        assert isinstance(command.id(), int)
        assert isinstance(command.user_id(), int)
        assert command.command() == command_name
        assert not command.parameters()
        assert not command.lifetime()
        assert isinstance(command.timestamp(), string)
        assert not command.status
        assert not command.result
        command_name = test.generate_id('send-command')
        parameters = 'parameters'
        lifetime = 10
        status = 'status'
        result = {'key': 'value'}
        command = device.send_command(command_name, parameters=parameters,
                                      lifetime=lifetime, status=status,
                                      result=result)
        assert command.device_id() == device_id
        assert isinstance(command.id(), int)
        assert isinstance(command.user_id(), int)
        assert command.command() == command_name
        assert command.parameters() == parameters
        assert command.lifetime() == lifetime
        assert isinstance(command.timestamp(), string)
        assert command.status == status
        assert command.result == result
        get_device = handler.api.get_device(device_id)
        device.remove()
        try:
            device.send_command(command_name)
            assert False
        except DeviceException:
            pass
        try:
            get_device.send_command(command_name)
            assert False
        except ApiResponseException as api_response_exception:
            # TODO: uncomment after server response will be fixed.
            # assert api_response_exception.code() == 404
            pass

    test.run(handle_connect)


def test_save(test):

    def handle_connect(handler):
        device_id = test.generate_id('save-command')
        command_name = test.generate_id('save-command')
        device = handler.api.put_device(device_id)
        command = device.send_command(command_name)
        status = 'status'
        result = {'key': 'value'}
        command.status = status
        command.result = result
        command.save()
        device.remove()
        try:
            command.save()
            assert False
        except ApiResponseException as api_response_exception:
            # TODO: uncomment after server response will be fixed.
            # assert api_response_exception.code() == 404
            pass

    test.run(handle_connect)
