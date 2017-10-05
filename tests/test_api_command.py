from devicehive import ApiResponseError


def test_save(test):
    device_hive_api = test.device_hive_api()
    device_id = test.generate_id('c-s')
    command_name = test.generate_id('c-s')
    device = device_hive_api.put_device(device_id)
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
        if test.admin_refresh_token:
            assert api_response_error.code == 404
        # TODO: uncomment after server response for ws for user token will
        # be fixed
        # else:
        #     assert api_response_error.code == 403
