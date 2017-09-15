from devicehive import ApiResponseError


def test_save(test):

    def handle_connect(handler):
        device_id = test.generate_id('c-s')
        command_name = test.generate_id('c-s')
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
            # TODO: remove ws check after server response codes for ws for user
            # token will be fixed
            if test.admin_refresh_token or test.websocket_transport:
                assert api_response_error.code == 404
            else:
                assert api_response_error.code == 403

    test.run(handle_connect)
