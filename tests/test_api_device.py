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


from devicehive import DeviceError, SubscriptionError
from devicehive import ApiResponseError
from devicehive.subscription import CommandsSubscription, \
    NotificationsSubscription


def test_save(test):
    device_hive_api = test.device_hive_api()
    device_id = test.generate_id('d-s', test.DEVICE_ENTITY)
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
    assert isinstance(device.device_type_id, int)
    assert device.is_blocked
    device.remove()
    try:
        device.save()
        assert False
    except DeviceError:
        pass


def test_remove(test):
    device_hive_api = test.device_hive_api()
    device_id = test.generate_id('d-r', test.DEVICE_ENTITY)
    device = device_hive_api.put_device(device_id)
    device_1 = device_hive_api.get_device(device_id)
    device.remove()
    assert not device.id
    assert not device.name
    assert not device.data
    assert not device.network_id
    assert not device.device_type_id
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
        if test.is_user_admin:
            assert api_response_error.code == 404
        else:
            assert api_response_error.code == 403


def test_subscribe_insert_commands(test):

    def init_data(handler):
        device_id = test.generate_id('d-s-i-c', test.DEVICE_ENTITY)
        command_names = ['%s-name-%s' % (device_id, i) for i in range(2)]
        device = handler.api.put_device(device_id)
        return device, command_names, []

    def send_data(handler, device, command_names):
        for command_name in command_names:
            command = device.send_command(command_name)
            handler.data['command_ids'].append(command.id)

    def set_handler_data(handler, device, command_names, command_ids):
        handler.data['device'] = device
        handler.data['command_names'] = command_names
        handler.data['command_ids'] = command_ids

    def handle_connect(handler):
        device, command_names, command_ids = init_data(handler)
        set_handler_data(handler, device, command_names, command_ids)
        send_data(handler, device, command_names)
        handler.data['subscription'] = device.subscribe_insert_commands()

    def handle_command_insert(handler, command):
        assert command.id in handler.data['command_ids']
        handler.data['command_ids'].remove(command.id)
        if handler.data['command_ids']:
            return
        handler.data['subscription'].remove()
        handler.data['device'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_command_insert)

    def handle_connect(handler):
        device, command_names, command_ids = init_data(handler)
        command_name = command_names[:1]
        set_handler_data(handler, device, command_names, command_ids)
        send_data(handler, device, command_name)
        handler.data['subscription'] = device.subscribe_insert_commands(
            names=command_name)

    def handle_command_insert(handler, command):
        assert command.id == handler.data['command_ids'][0]
        handler.data['subscription'].remove()
        handler.data['device'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_command_insert)

    def handle_connect(handler):
        device, commands, command_ids = init_data(handler)
        device_1 = handler.api.get_device(device.id)
        device.remove()
        # TODO: remove when subscription probe will be done.
        if test.http_transport:
            return
        try:
            device_1.subscribe_insert_commands()
            assert False
        except ApiResponseError as api_response_error:
            if test.is_user_admin:
                assert api_response_error.code == 404
            else:
                assert api_response_error.code == 403

    test.run(handle_connect)


def test_unsubscribe_insert_commands(test):

    def handle_connect(handler):
        device_id = test.generate_id('d-u-i-c', test.DEVICE_ENTITY)
        device = handler.api.put_device(device_id)
        subscription = device.subscribe_insert_commands()
        subscription_1 = CommandsSubscription(
            handler.api, {'subscriptionId': subscription.id})
        subscription.remove()
        try:
            subscription.remove()
            assert False
        except SubscriptionError:
            pass
        try:
            subscription_1.remove()
            assert False
        except ApiResponseError as api_response_error:
            assert api_response_error.code == 404

        device.remove()

    test.run(handle_connect)


def test_subscribe_update_commands(test):

    def init_data(handler):
        device_id = test.generate_id('d-s-u-c', test.DEVICE_ENTITY)
        command_names = ['%s-name-%s' % (device_id, i) for i in range(2)]
        device = handler.api.put_device(device_id)
        return device, command_names, []

    def send_data(handler, device, command_names):
        for command_name in command_names:
            command = device.send_command(command_name)
            handler.data['command_ids'].append(command.id)
            command.status = 'status'
            command.save()

    def set_handler_data(handler, device, command_names, command_ids):
        handler.data['device'] = device
        handler.data['command_names'] = command_names
        handler.data['command_ids'] = command_ids

    def handle_connect(handler):
        device, command_names, command_ids = init_data(handler)
        set_handler_data(handler, device, command_names, command_ids)
        send_data(handler, device, command_names)
        handler.data['subscription'] = device.subscribe_update_commands()

    def handle_command_update(handler, command):
        assert command.id in handler.data['command_ids']
        handler.data['command_ids'].remove(command.id)
        if handler.data['command_ids']:
            return
        handler.data['subscription'].remove()
        handler.data['device'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_command_update=handle_command_update)

    def handle_connect(handler):
        device, command_names, command_ids = init_data(handler)
        command_name = command_names[:1]
        set_handler_data(handler, device, command_names, command_ids)
        send_data(handler, device, command_name)
        handler.data['subscription'] = device.subscribe_update_commands(
            names=command_name)

    def handle_command_update(handler, command):
        assert command.id == handler.data['command_ids'][0]
        handler.data['subscription'].remove()
        handler.data['device'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_command_update=handle_command_update)

    def handle_connect(handler):
        device, commands, command_ids = init_data(handler)
        device_1 = handler.api.get_device(device.id)
        device.remove()
        # TODO: remove when subscription probe will be done.
        if test.http_transport:
            return
        try:
            device_1.subscribe_update_commands()
            assert False
        except ApiResponseError as api_response_error:
            if test.is_user_admin:
                assert api_response_error.code == 404
            else:
                assert api_response_error.code == 403

    test.run(handle_connect)


def test_unsubscribe_update_commands(test):

    def handle_connect(handler):
        device_id = test.generate_id('d-u-u-c', test.DEVICE_ENTITY)
        device = handler.api.put_device(device_id)
        subscription = device.subscribe_update_commands()
        subscription_1 = CommandsSubscription(
            handler.api, {'subscriptionId': subscription.id})
        subscription.remove()
        try:
            subscription.remove()
            assert False
        except SubscriptionError:
            pass
        try:
            subscription_1.remove()
            assert False
        except ApiResponseError as api_response_error:
            assert api_response_error.code == 404

        device.remove()

    test.run(handle_connect)


def test_list_commands(test):
    device_hive_api = test.device_hive_api()
    server_timestamp = device_hive_api.get_info()['server_timestamp']
    test_id = test.generate_id('d-l-c', test.DEVICE_ENTITY)
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
        if test.is_user_admin:
            assert api_response_error.code == 404
        else:
            assert api_response_error.code == 403


def test_send_command(test):
    device_hive_api = test.device_hive_api()
    device_id = test.generate_id('d-s-c', test.DEVICE_ENTITY)
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
        if test.is_user_admin:
            assert api_response_error.code == 404
        else:
            assert api_response_error.code == 403


def test_subscribe_notifications(test):

    def init_data(handler):
        device_id = test.generate_id('d-s-n', test.DEVICE_ENTITY)
        notification_names = ['%s-name-%s' % (device_id, i) for i in range(2)]
        device = handler.api.put_device(device_id)
        return device, notification_names, []

    def send_data(handler, device, notification_names):
        for notification_name in notification_names:
            notification = device.send_notification(notification_name)
            handler.data['notification_ids'].append(notification.id)

    def set_handler_data(handler, device, notification_names,
                         notification_ids):
        handler.data['device'] = device
        handler.data['notification_names'] = notification_names
        handler.data['notification_ids'] = notification_ids

    def handle_connect(handler):
        device, notification_names, notification_ids = init_data(handler)
        set_handler_data(handler, device, notification_names, notification_ids)
        send_data(handler, device, notification_names)
        handler.data['subscription'] = device.subscribe_notifications()

    def handle_notification(handler, notification):
        assert notification.id in handler.data['notification_ids']
        handler.data['notification_ids'].remove(notification.id)
        if handler.data['notification_ids']:
            return
        handler.data['subscription'].remove()
        handler.data['device'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_notification=handle_notification)

    def handle_connect(handler):
        device, notification_names, notification_ids = init_data(handler)
        notification_name = notification_names[:1]
        set_handler_data(handler, device, notification_names, notification_ids)
        send_data(handler, device, notification_name)
        handler.data['subscription'] = device.subscribe_notifications(
            names=notification_name)

    def handle_notification(handler, notification):
        assert notification.id == handler.data['notification_ids'][0]
        handler.data['subscription'].remove()
        handler.data['device'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_notification=handle_notification)

    def handle_connect(handler):
        device, notification_names, notification_ids = init_data(handler)

        device_1 = handler.api.get_device(device.id)
        device.remove()
        # TODO: remove when subscription probe will be done.
        if test.http_transport:
            return
        try:
            device_1.subscribe_notifications()
            assert False
        except ApiResponseError as api_response_error:
            if test.is_user_admin:
                assert api_response_error.code == 404
            else:
                assert api_response_error.code == 403

    test.run(handle_connect)


def test_unsubscribe_notifications(test):

    def handle_connect(handler):
        device_id = test.generate_id('d-u-n', test.DEVICE_ENTITY)
        device = handler.api.put_device(device_id)
        subscription = device.subscribe_notifications()
        subscription_1 = NotificationsSubscription(
            handler.api, {'subscriptionId': subscription.id})
        subscription.remove()
        try:
            subscription.remove()
            assert False
        except SubscriptionError:
            pass
        try:
            subscription_1.remove()
            assert False
        except ApiResponseError as api_response_error:
            assert api_response_error.code == 404

        device.remove()

    test.run(handle_connect)


def list_notifications(device, **params):
    notifications = device.list_notifications(**params)
    return [notification for notification in notifications
            if notification.notification[0] != '$']


def test_list_notifications(test):
    device_hive_api = test.device_hive_api()
    server_timestamp = device_hive_api.get_info()['server_timestamp']
    test_id = test.generate_id('d-l-n', test.DEVICE_ENTITY)
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
        if test.is_user_admin:
            assert api_response_error.code == 404
        else:
            assert api_response_error.code == 403


def test_send_notification(test):
    device_hive_api = test.device_hive_api()
    device_id = test.generate_id('d-s-n', test.DEVICE_ENTITY)
    notification_name = test.generate_id('d-s-n')
    device = device_hive_api.put_device(device_id)
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
    device_1 = device_hive_api.get_device(device_id)
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
        if test.is_user_admin:
            assert api_response_error.code == 404
        else:
            assert api_response_error.code == 403
