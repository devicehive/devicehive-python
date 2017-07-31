from devicehive import ApiResponseError


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
