# Copyright (C) 2018 DataArt
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================


from devicehive import ApiResponseError


def test_save(test):
    device_hive_api = test.device_hive_api()
    device_id = test.generate_id('c-s', test.DEVICE_ENTITY)
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
        if test.is_user_admin:
            assert api_response_error.code == 404
        else:
            assert api_response_error.code == 403
