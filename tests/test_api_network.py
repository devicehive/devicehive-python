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


from devicehive import NetworkError, ApiResponseError, SubscriptionError
from devicehive.subscription import CommandsSubscription, \
    NotificationsSubscription


def test_save(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()
    name = test.generate_id('n-s', test.NETWORK_ENTITY)
    description = '%s-description' % name
    network = device_hive_api.create_network(name, description)
    name = test.generate_id('n-s', test.NETWORK_ENTITY)
    description = '%s-description' % name
    network.name = name
    network.description = description
    network.save()
    network_1 = device_hive_api.get_network(network.id)
    network.remove()
    try:
        network.save()
        assert False
    except NetworkError:
        pass
    try:
        network_1.save()
        assert False
    except ApiResponseError as api_response_error:
        assert api_response_error.code == 404


def test_remove(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()
    name = test.generate_id('n-r', test.NETWORK_ENTITY)
    description = '%s-description' % name
    network = device_hive_api.create_network(name, description)
    network_1 = device_hive_api.get_network(network.id)
    network.remove()
    assert not network.id
    assert not network.name
    assert not network.description
    try:
        network.remove()
        assert False
    except NetworkError:
        pass
    try:
        network_1.remove()
        assert False
    except ApiResponseError as api_response_error:
        assert api_response_error.code == 404

    # ==========================================================================
    name = test.generate_id('n-r', test.NETWORK_ENTITY)
    description = '%s-description' % name
    network = device_hive_api.create_network(name, description)

    device_id = test.generate_id('n-r', test.DEVICE_ENTITY)
    device_hive_api.put_device(device_id, network_id=network.id)

    try:
        network.remove()
        assert False
    except ApiResponseError as api_response_error:
        assert api_response_error.code == 400
        device = device_hive_api.get_device(device_id)
        assert device.id == device_id

    network.remove(force=True)
    try:
        device_hive_api.get_device(device_id)
        assert False
    except ApiResponseError as api_response_error:
        assert api_response_error.code == 404


def test_subscribe_insert_commands(test):
    test.only_admin_implementation()

    def init_data(handler):
        device_id = test.generate_id('n-s-i-c', test.DEVICE_ENTITY)
        network_name = test.generate_id('n-s-i-c', test.NETWORK_ENTITY)
        description = '%s-description' % network_name
        network = handler.api.create_network(network_name, description)
        command_names = ['%s-name-%s' % (device_id, i) for i in range(2)]
        device = handler.api.put_device(device_id, network_id=network.id)
        return device, network, command_names, []

    def send_data(handler, device, command_names):
        for command_name in command_names:
            command = device.send_command(command_name)
            handler.data['command_ids'].append(command.id)

    def set_handler_data(handler, device, network, command_names, command_ids):
        handler.data['device'] = device
        handler.data['network'] = network
        handler.data['command_names'] = command_names
        handler.data['command_ids'] = command_ids

    def handle_connect(handler):
        device, network, command_names, command_ids = init_data(handler)
        set_handler_data(handler, device, network, command_names, command_ids)
        send_data(handler, device, command_names)
        network.subscribe_insert_commands()

    def handle_command_insert(handler, command):
        assert command.id in handler.data['command_ids']
        handler.data['command_ids'].remove(command.id)
        if handler.data['command_ids']:
            return
        handler.data['device'].remove()
        handler.data['network'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_command_insert)

    def handle_connect(handler):
        device, network, command_names, command_ids = init_data(handler)
        command_name = command_names[:1]
        set_handler_data(handler, device, network, command_names, command_ids)
        send_data(handler, device, command_name)
        network.subscribe_insert_commands(names=command_name)

    def handle_command_insert(handler, command):
        assert command.id == handler.data['command_ids'][0]
        handler.data['device'].remove()
        handler.data['network'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_command_insert)

    def handle_connect(handler):
        network_name = test.generate_id('n-s-i-c', test.NETWORK_ENTITY)
        description = '%s-description' % network_name
        network = handler.api.create_network(network_name, description)
        network.subscribe_insert_commands()
        device_id = test.generate_id('n-s-i-c', test.DEVICE_ENTITY)
        device = handler.api.put_device(device_id, network_id=network.id)
        command_name = '%s-name-1' % device_id
        command = device.send_command(command_name)

        set_handler_data(handler, device, network, [command_name], [command.id])

    def handle_command_insert(handler, command):
        assert command.id == handler.data['command_ids'][0]
        handler.data['device'].remove()
        handler.data['network'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_command_insert)

    def handle_connect(handler):
        network_name = test.generate_id('n-s-i-c', test.NETWORK_ENTITY)
        description = '%s-description' % network_name
        network = handler.api.create_network(network_name, description)

        network.subscribe_insert_commands()
        network_1 = handler.api.get_network(network.id)
        network.remove()
        if test.http_transport:
            return
        try:
            network_1.subscribe_insert_commands()
            assert False
        except ApiResponseError as api_response_error:
            assert api_response_error.code == 404

    test.run(handle_connect)


def test_unsubscribe_insert_commands(test):
    test.only_admin_implementation()

    def handle_connect(handler):
        name = test.generate_id('n-u-i-c', test.NETWORK_ENTITY)
        description = '%s-description' % name
        network = handler.api.create_network(name, description)
        subscription = network.subscribe_insert_commands()
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

        network.remove()

    test.run(handle_connect)


def test_subscribe_update_commands(test):
    test.only_admin_implementation()

    def init_data(handler):
        device_id = test.generate_id('n-s-u-c', test.DEVICE_ENTITY)
        network_name = test.generate_id('n-s-u-c', test.NETWORK_ENTITY)
        description = '%s-description' % network_name
        network = handler.api.create_network(network_name, description)
        command_names = ['%s-name-%s' % (device_id, i) for i in range(2)]
        device = handler.api.put_device(device_id, network_id=network.id)
        return device, network, command_names, []

    def send_data(handler, device, command_names):
        for command_name in command_names:
            command = device.send_command(command_name)
            handler.data['command_ids'].append(command.id)
            command.status = 'status'
            command.save()

    def set_handler_data(handler, device, network, command_names, command_ids):
        handler.data['device'] = device
        handler.data['network'] = network
        handler.data['command_names'] = command_names
        handler.data['command_ids'] = command_ids

    def handle_connect(handler):
        device, network, command_names, command_ids = init_data(handler)
        set_handler_data(handler, device, network, command_names, command_ids)
        send_data(handler, device, command_names)
        network.subscribe_update_commands()

    def handle_command_update(handler, command):
        assert command.id in handler.data['command_ids']
        handler.data['command_ids'].remove(command.id)
        if handler.data['command_ids']:
            return
        handler.data['device'].remove()
        handler.data['network'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_command_update=handle_command_update)

    def handle_connect(handler):
        device, network, command_names, command_ids = init_data(handler)
        command_name = command_names[:1]
        set_handler_data(handler, device, network, command_names, command_ids)
        send_data(handler, device, command_name)
        network.subscribe_update_commands(names=command_name)

    def handle_command_update(handler, command):
        assert command.id == handler.data['command_ids'][0]
        handler.data['device'].remove()
        handler.data['network'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_command_update=handle_command_update)

    def handle_connect(handler):
        network_name = test.generate_id('n-s-u-c', test.NETWORK_ENTITY)
        description = '%s-description' % network_name
        network = handler.api.create_network(network_name, description)
        network.subscribe_update_commands()
        device_id = test.generate_id('n-s-u-c', test.DEVICE_ENTITY)
        device = handler.api.put_device(device_id, network_id=network.id)
        command_name = '%s-name-1' % device_id
        command = device.send_command(command_name)
        command.status = 'status'
        command.save()

        set_handler_data(handler, device, network, [command_name], [command.id])

    def handle_command_update(handler, command):
        assert command.id == handler.data['command_ids'][0]
        handler.data['device'].remove()
        handler.data['network'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_command_update=handle_command_update)

    def handle_connect(handler):
        network_name = test.generate_id('n-s-u-c', test.NETWORK_ENTITY)
        description = '%s-description' % network_name
        network = handler.api.create_network(network_name, description)

        network.subscribe_update_commands()
        network_1 = handler.api.get_network(network.id)
        network.remove()
        if test.http_transport:
            return
        try:
            network_1.subscribe_update_commands()
            assert False
        except ApiResponseError as api_response_error:
            assert api_response_error.code == 404

    test.run(handle_connect)


def test_unsubscribe_update_commands(test):
    test.only_admin_implementation()

    def handle_connect(handler):
        name = test.generate_id('n-u-u-c', test.NETWORK_ENTITY)
        description = '%s-description' % name
        network = handler.api.create_network(name, description)
        subscription = network.subscribe_update_commands()
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

        network.remove()

    test.run(handle_connect)


def test_subscribe_notifications(test):
    test.only_admin_implementation()

    def init_data(handler):
        device_id = test.generate_id('n-s-n', test.DEVICE_ENTITY)
        network_name = test.generate_id('n-s-n', test.NETWORK_ENTITY)
        description = '%s-description' % network_name
        network = handler.api.create_network(network_name, description)
        notification_names = ['%s-name-%s' % (device_id, i) for i in range(2)]
        device = handler.api.put_device(device_id, network_id=network.id)
        return device, network, notification_names, []

    def send_data(handler, device, notification_names):
        for notification_name in notification_names:
            notification = device.send_notification(notification_name)
            handler.data['notification_ids'].append(notification.id)

    def set_handler_data(handler, device, network, notification_names,
                         notification_ids):
        handler.data['device'] = device
        handler.data['network'] = network
        handler.data['notification_names'] = notification_names
        handler.data['notification_ids'] = notification_ids

    def handle_connect(handler):
        device, network, notification_names, notification_ids = init_data(
            handler)
        set_handler_data(handler, device, network, notification_names,
                         notification_ids)
        send_data(handler, device, notification_names)
        network.subscribe_notifications()

    def handle_notification(handler, notification):
        assert notification.id in handler.data['notification_ids']
        handler.data['notification_ids'].remove(notification.id)
        if handler.data['notification_ids']:
            return
        handler.data['device'].remove()
        handler.data['network'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_notification=handle_notification)

    def handle_connect(handler):
        device, network, notification_names, notification_ids = init_data(
            handler)
        notification_name = notification_names[:1]
        network.subscribe_notifications(names=notification_name)
        set_handler_data(handler, device, network, notification_names,
                         notification_ids)
        send_data(handler, device, notification_name)

    def handle_notification(handler, notification):
        assert notification.id == handler.data['notification_ids'][0]
        handler.data['device'].remove()
        handler.data['network'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_notification=handle_notification)

    def handle_connect(handler):
        network_name = test.generate_id('n-s-n', test.NETWORK_ENTITY)
        description = '%s-description' % network_name
        network = handler.api.create_network(network_name, description)
        network.subscribe_notifications()
        device_id = test.generate_id('n-s-n', test.DEVICE_ENTITY)
        device = handler.api.put_device(device_id, network_id=network.id)
        notification_name = '%s-name-1' % device_id
        notification = device.send_notification(notification_name)

        set_handler_data(handler, device, network, [notification_name],
                         [notification.id])

    def handle_notification(handler, notification):
        assert notification.id == handler.data['notification_ids'][0]
        handler.data['device'].remove()
        handler.data['network'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_notification=handle_notification)

    def handle_connect(handler):
        network_name = test.generate_id('n-s-n', test.NETWORK_ENTITY)
        description = '%s-description' % network_name
        network = handler.api.create_network(network_name, description)

        network.subscribe_notifications()
        network_1 = handler.api.get_network(network.id)
        network.remove()
        if test.http_transport:
            return
        try:
            network_1.subscribe_notifications()
            assert False
        except ApiResponseError as api_response_error:
            assert api_response_error.code == 404

    test.run(handle_connect)


def test_unsubscribe_notifications(test):
    test.only_admin_implementation()

    def handle_connect(handler):
        name = test.generate_id('n-u-n', test.NETWORK_ENTITY)
        description = '%s-description' % name
        network = handler.api.create_network(name, description)
        subscription = network.subscribe_notifications()
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

        network.remove()

    test.run(handle_connect)
