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


from six import string_types
from devicehive import ApiResponseError, SubscriptionError
from devicehive.subscription import CommandsSubscription, \
    NotificationsSubscription
from devicehive.user import User


def test_get_info(test):
    device_hive_api = test.device_hive_api()
    info = device_hive_api.get_info()
    assert isinstance(info['api_version'], string_types)
    assert isinstance(info['server_timestamp'], string_types)
    if info.get('rest_server_url'):
        assert info['websocket_server_url'] is None
        assert isinstance(info['rest_server_url'], string_types)
        return
    assert isinstance(info['websocket_server_url'], string_types)
    assert info['rest_server_url'] is None


def test_get_cluster_info(test):
    device_hive_api = test.device_hive_api()
    cluster_info = device_hive_api.get_cluster_info()
    assert isinstance(cluster_info['bootstrap.servers'], string_types)
    assert isinstance(cluster_info['zookeeper.connect'], string_types)


def test_create_token(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()
    login = test.generate_id('c-t', test.USER_ENTITY)
    password = test.generate_id('c-t')
    role = User.ADMINISTRATOR_ROLE
    data = {'k': 'v'}
    user = device_hive_api.create_user(login, password, role, data)
    tokens = device_hive_api.create_token(user.id)
    assert isinstance(tokens['access_token'], string_types)
    assert isinstance(tokens['refresh_token'], string_types)
    user_id = user.id
    user.remove()
    try:
        device_hive_api.create_token(user_id)
        assert False
    except ApiResponseError as api_response_error:
        assert api_response_error.code == 404


def test_refresh_token(test):
    test.not_access_token_cred_implementation()
    device_hive_api = test.device_hive_api()
    access_token = device_hive_api.refresh_token()
    assert isinstance(access_token, string_types)


def test_subscribe_insert_commands(test):
    test.only_admin_implementation()

    def init_data(handler):
        network_name = test.generate_id('s-i-c', test.NETWORK_ENTITY)
        network_description = '%s-description' % network_name
        network = handler.api.create_network(network_name, network_description)

        device_type_name = test.generate_id('s-i-c', test.DEVICE_TYPE_ENTITY)
        device_type_description = '%s-description' % device_type_name
        device_type = handler.api.create_device_type(device_type_name,
                                                     device_type_description)

        device_id = test.generate_id('s-i-c', test.DEVICE_ENTITY)
        device = handler.api.put_device(device_id, network_id=network.id,
                                        device_type_id=device_type.id)

        command_names = ['%s-name-%s' % (device_id, i) for i in range(2)]

        return device, network, device_type, command_names, []

    def send_data(handler, device, command_names):
        for command_name in command_names:
            command = device.send_command(command_name)
            handler.data['command_ids'].append(command.id)

    def set_handler_data(handler, device, network, device_type, command_names,
                         command_ids):
        handler.data['device'] = device
        handler.data['network'] = network
        handler.data['device_type'] = device_type
        handler.data['command_names'] = command_names
        handler.data['command_ids'] = command_ids

    def handle_connect(handler):
        device, network, device_type, command_names, command_ids = init_data(
            handler)
        set_handler_data(handler, device, network, device_type, command_names,
                         command_ids)
        send_data(handler, device, command_names)
        handler.data['subscription'] = handler.api.subscribe_insert_commands(
            network_ids=[network.id], device_type_ids=[device_type.id])

    def handle_command_insert(handler, command):
        assert command.id in handler.data['command_ids']
        handler.data['command_ids'].remove(command.id)
        if handler.data['command_ids']:
            return
        handler.data['subscription'].remove()
        handler.data['device'].remove()
        handler.data['network'].remove()
        handler.data['device_type'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_command_insert)

    def handle_connect(handler):
        device, network, device_type, command_names, command_ids = init_data(
            handler)
        command_name = command_names[:1]
        set_handler_data(handler, device, network, device_type, command_names,
                         command_ids)
        send_data(handler, device, command_name)
        handler.data['subscription'] = handler.api.subscribe_insert_commands(
            network_ids=[network.id], device_type_ids=[device_type.id],
            names=command_name)

    def handle_command_insert(handler, command):
        assert command.id == handler.data['command_ids'][0]
        handler.data['subscription'].remove()
        handler.data['device'].remove()
        handler.data['network'].remove()
        handler.data['device_type'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_command_insert)

    def handle_connect(handler):
        network_name = test.generate_id('s-i-c', test.NETWORK_ENTITY)
        network_description = '%s-description' % network_name
        network = handler.api.create_network(network_name, network_description)

        device_type_name = test.generate_id('s-i-c', test.DEVICE_TYPE_ENTITY)
        device_type_description = '%s-description' % device_type_name
        device_type = handler.api.create_device_type(device_type_name,
                                                     device_type_description)


        device_id = test.generate_id('s-i-c', test.DEVICE_ENTITY)
        device = handler.api.put_device(device_id, network_id=network.id,
                                        device_type_id=device_type.id)
        command_name = '%s-name-1' % device_id
        command = device.send_command(command_name)

        set_handler_data(handler, device, network, device_type, [command_name],
                         [command.id])
        handler.data['subscription'] = handler.api.subscribe_insert_commands(
            network_ids=[network.id], device_type_ids=[device_type.id])

    def handle_command_insert(handler, command):
        assert command.id == handler.data['command_ids'][0]
        handler.data['subscription'].remove()
        handler.data['device'].remove()
        handler.data['network'].remove()
        handler.data['device_type'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_command_insert)


def test_unsubscribe_insert_commands(test):
    test.only_admin_implementation()

    def handle_connect(handler):
        network_name = test.generate_id('u-i-c', test.NETWORK_ENTITY)
        network_description = '%s-description' % network_name
        network = handler.api.create_network(network_name, network_description)

        device_type_name = test.generate_id('u-i-c', test.DEVICE_TYPE_ENTITY)
        device_type_description = '%s-description' % device_type_name
        device_type = handler.api.create_device_type(device_type_name,
                                                     device_type_description)

        subscription = handler.api.subscribe_insert_commands(
            network_ids=[network.id], device_type_ids=[device_type.id])
        subscription.remove()
        try:
            subscription.remove()
            assert False
        except SubscriptionError:
            pass

        network.remove()
        device_type.remove()

    test.run(handle_connect)


def test_subscribe_update_commands(test):
    test.only_admin_implementation()

    def init_data(handler):
        network_name = test.generate_id('s-u-c', test.NETWORK_ENTITY)
        network_description = '%s-description' % network_name
        network = handler.api.create_network(network_name, network_description)

        device_type_name = test.generate_id('s-u-c', test.DEVICE_TYPE_ENTITY)
        device_type_description = '%s-description' % device_type_name
        device_type = handler.api.create_device_type(device_type_name,
                                                     device_type_description)

        device_id = test.generate_id('s-u-c', test.DEVICE_ENTITY)
        device = handler.api.put_device(device_id, network_id=network.id,
                                        device_type_id=device_type.id)

        command_names = ['%s-name-%s' % (device_id, i) for i in range(2)]

        return device, network, device_type, command_names, []

    def send_data(handler, device, command_names):
        for command_name in command_names:
            command = device.send_command(command_name)
            handler.data['command_ids'].append(command.id)
            command.status = 'status'
            command.save()

    def set_handler_data(handler, device, network, device_type, command_names,
                         command_ids):
        handler.data['device'] = device
        handler.data['network'] = network
        handler.data['device_type'] = device_type
        handler.data['command_names'] = command_names
        handler.data['command_ids'] = command_ids

    def handle_connect(handler):
        device, network, device_type, command_names, command_ids = init_data(
            handler)
        set_handler_data(handler, device, network, device_type, command_names,
                         command_ids)
        send_data(handler, device, command_names)
        handler.data['subscription'] = handler.api.subscribe_update_commands(
            network_ids=[network.id], device_type_ids=[device_type.id])

    def handle_command_update(handler, command):
        assert command.id in handler.data['command_ids']
        handler.data['command_ids'].remove(command.id)
        if handler.data['command_ids']:
            return
        handler.data['subscription'].remove()
        handler.data['device'].remove()
        handler.data['network'].remove()
        handler.data['device_type'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_command_update=handle_command_update)

    def handle_connect(handler):
        device, network, device_type, command_names, command_ids = init_data(
            handler)
        command_name = command_names[:1]
        set_handler_data(handler, device, network, device_type, command_names,
                         command_ids)
        send_data(handler, device, command_name)
        handler.data['subscription'] = handler.api.subscribe_update_commands(
            network_ids=[network.id], device_type_ids=[device_type.id],
            names=command_name)

    def handle_command_update(handler, command):
        assert command.id == handler.data['command_ids'][0]
        handler.data['subscription'].remove()
        handler.data['device'].remove()
        handler.data['network'].remove()
        handler.data['device_type'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_command_update=handle_command_update)

    def handle_connect(handler):
        network_name = test.generate_id('s-u-c', test.NETWORK_ENTITY)
        network_description = '%s-description' % network_name
        network = handler.api.create_network(network_name, network_description)

        device_type_name = test.generate_id('s-u-c', test.DEVICE_TYPE_ENTITY)
        device_type_description = '%s-description' % device_type_name
        device_type = handler.api.create_device_type(device_type_name,
                                                     device_type_description)


        device_id = test.generate_id('s-u-c', test.DEVICE_ENTITY)
        device = handler.api.put_device(device_id, network_id=network.id,
                                        device_type_id=device_type.id)
        command_name = '%s-name-1' % device_id
        command = device.send_command(command_name)
        command.status = 'status'
        command.save()

        set_handler_data(handler, device, network, device_type, [command_name],
                         [command.id])
        handler.data['subscription'] = handler.api.subscribe_update_commands(
            network_ids=[network.id], device_type_ids=[device_type.id])

    def handle_command_update(handler, command):
        assert command.id == handler.data['command_ids'][0]
        handler.data['subscription'].remove()
        handler.data['device'].remove()
        handler.data['network'].remove()
        handler.data['device_type'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_command_update=handle_command_update)


def test_unsubscribe_update_commands(test):
    test.only_admin_implementation()

    def handle_connect(handler):
        network_name = test.generate_id('u-u-c', test.NETWORK_ENTITY)
        network_description = '%s-description' % network_name
        network = handler.api.create_network(network_name, network_description)

        device_type_name = test.generate_id('u-u-c', test.DEVICE_TYPE_ENTITY)
        device_type_description = '%s-description' % device_type_name
        device_type = handler.api.create_device_type(device_type_name,
                                                     device_type_description)

        subscription = handler.api.subscribe_update_commands(
            network_ids=[network.id], device_type_ids=[device_type.id])
        subscription.remove()
        try:
            subscription.remove()
            assert False
        except SubscriptionError:
            pass

        network.remove()
        device_type.remove()

    test.run(handle_connect)


def test_subscribe_notifications(test):
    test.only_admin_implementation()

    def init_data(handler):
        network_name = test.generate_id('s-n', test.NETWORK_ENTITY)
        network_description = '%s-description' % network_name
        network = handler.api.create_network(network_name, network_description)

        device_type_name = test.generate_id('s-n', test.DEVICE_TYPE_ENTITY)
        device_type_description = '%s-description' % device_type_name
        device_type = handler.api.create_device_type(device_type_name,
                                                     device_type_description)

        device_id = test.generate_id('s-n', test.DEVICE_ENTITY)
        device = handler.api.put_device(device_id, network_id=network.id,
                                        device_type_id=device_type.id)

        command_names = ['%s-name-%s' % (device_id, i) for i in range(2)]

        return device, network, device_type, command_names, []

    def send_data(handler, device, notification_names):
        for notification_name in notification_names:
            notification = device.send_notification(notification_name)
            handler.data['notification_ids'].append(notification.id)

    def set_handler_data(handler, device, network, device_type,
                         notification_names, notification_ids):
        handler.data['device'] = device
        handler.data['network'] = network
        handler.data['device_type'] = device_type
        handler.data['notification_names'] = notification_names
        handler.data['notification_ids'] = notification_ids

    def handle_connect(handler):
        device, network, device_type, notification_names, notification_ids = \
            init_data(handler)
        set_handler_data(handler, device, network, device_type,
                         notification_names, notification_ids)
        send_data(handler, device, notification_names)
        handler.data['subscription'] = handler.api.subscribe_notifications(
            network_ids=[network.id], device_type_ids=[device_type.id])

    def handle_notification(handler, notification):
        assert notification.id in handler.data['notification_ids']
        handler.data['notification_ids'].remove(notification.id)
        if handler.data['notification_ids']:
            return
        handler.data['subscription'].remove()
        handler.data['device'].remove()
        handler.data['network'].remove()
        handler.data['device_type'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_notification=handle_notification)

    def handle_connect(handler):
        device, network, device_type, notification_names, notification_ids = \
            init_data(handler)
        notification_name = notification_names[:1]
        set_handler_data(handler, device, network, device_type,
                         notification_names, notification_ids)
        send_data(handler, device, notification_name)
        handler.data['subscription'] = handler.api.subscribe_notifications(
            network_ids=[network.id], device_type_ids=[device_type.id],
            names=notification_name)

    def handle_notification(handler, notification):
        assert notification.id == handler.data['notification_ids'][0]
        handler.data['subscription'].remove()
        handler.data['device'].remove()
        handler.data['network'].remove()
        handler.data['device_type'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_notification=handle_notification)

    def handle_connect(handler):
        network_name = test.generate_id('s-n', test.NETWORK_ENTITY)
        network_description = '%s-description' % network_name
        network = handler.api.create_network(network_name, network_description)

        device_type_name = test.generate_id('s-n', test.DEVICE_TYPE_ENTITY)
        device_type_description = '%s-description' % device_type_name
        device_type = handler.api.create_device_type(device_type_name,
                                                     device_type_description)


        device_id = test.generate_id('s-n', test.DEVICE_ENTITY)
        device = handler.api.put_device(device_id, network_id=network.id,
                                        device_type_id=device_type.id)
        notification_name = '%s-name-1' % device_id
        notification = device.send_notification(notification_name)

        set_handler_data(handler, device, network, device_type,
                         [notification_name], [notification.id])
        handler.data['subscription'] = handler.api.subscribe_notifications(
            network_ids=[network.id], device_type_ids=[device_type.id])

    def handle_notification(handler, notification):
        assert notification.id == handler.data['notification_ids'][0]
        handler.data['subscription'].remove()
        handler.data['device'].remove()
        handler.data['network'].remove()
        handler.data['device_type'].remove()
        handler.disconnect()

    test.run(handle_connect, handle_notification=handle_notification)


def test_unsubscribe_notifications(test):
    test.only_admin_implementation()

    def handle_connect(handler):
        network_name = test.generate_id('u-n', test.NETWORK_ENTITY)
        network_description = '%s-description' % network_name
        network = handler.api.create_network(network_name, network_description)

        device_type_name = test.generate_id('u-n', test.DEVICE_TYPE_ENTITY)
        device_type_description = '%s-description' % device_type_name
        device_type = handler.api.create_device_type(device_type_name,
                                                     device_type_description)

        subscription = handler.api.subscribe_notifications(
            network_ids=[network.id], device_type_ids=[device_type.id])
        subscription.remove()
        try:
            subscription.remove()
            assert False
        except SubscriptionError:
            pass

        network.remove()
        device_type.remove()

    test.run(handle_connect)


def test_list_devices(test):
    device_hive_api = test.device_hive_api()
    test_id, device_ids = test.generate_ids('l-d', test.DEVICE_ENTITY, 2)
    options = [{'device_id': device_id, 'name': '%s-name' % device_id}
               for device_id in device_ids]
    test_devices = [device_hive_api.put_device(**option) for option in options]
    devices = device_hive_api.list_devices()
    assert len(devices) >= len(options)
    name = options[0]['name']
    device, = device_hive_api.list_devices(name=name)
    assert device.name == name
    name_pattern = test.generate_id('l-d-n-e')
    assert not device_hive_api.list_devices(name_pattern=name_pattern)
    name_pattern = test_id + '%'
    devices = device_hive_api.list_devices(name_pattern=name_pattern)
    assert len(devices) == len(options)
    device_0, device_1 = device_hive_api.list_devices(name_pattern=name_pattern,
                                                      sort_field='name',
                                                      sort_order='ASC')
    assert device_0.id == options[0]['device_id']
    assert device_1.id == options[1]['device_id']
    device_0, device_1 = device_hive_api.list_devices(name_pattern=name_pattern,
                                                      sort_field='name',
                                                      sort_order='DESC')
    assert device_0.id == options[1]['device_id']
    assert device_1.id == options[0]['device_id']
    device, = device_hive_api.list_devices(name_pattern=name_pattern,
                                           sort_field='name', sort_order='ASC',
                                           take=1)
    assert device.id == options[0]['device_id']
    device, = device_hive_api.list_devices(name_pattern=name_pattern,
                                           sort_field='name', sort_order='ASC',
                                           take=1, skip=1)
    assert device.id == options[1]['device_id']
    [test_device.remove() for test_device in test_devices]


def test_get_device(test):
    device_hive_api = test.device_hive_api()
    device_id = test.generate_id('g-d', test.DEVICE_ENTITY)
    name = '%s-name' % device_id
    data = {'data_key': 'data_value'}
    device_hive_api.put_device(device_id, name=name, data=data)
    device = device_hive_api.get_device(device_id)
    assert device.id == device_id
    assert device.name == name
    assert device.data == data
    assert isinstance(device.network_id, int)
    assert isinstance(device.device_type_id, int)
    assert not device.is_blocked
    device.remove()
    device_id = test.generate_id('g-d-n-e')
    try:
        device_hive_api.get_device(device_id)
        assert False
    except ApiResponseError as api_response_error:
        if test.is_user_admin:
            assert api_response_error.code == 404
        else:
            assert api_response_error.code == 403


def test_put_device(test):
    device_hive_api = test.device_hive_api()
    device_id = test.generate_id('p-d', test.DEVICE_ENTITY)
    device = device_hive_api.put_device(device_id)
    assert device.id == device_id
    assert device.name == device_id
    assert not device.data
    assert isinstance(device.network_id, int)
    assert isinstance(device.device_type_id, int)
    assert not device.is_blocked
    device.remove()
    name = '%s-name' % device_id
    data = {'data_key': 'data_value'}
    device = device_hive_api.put_device(device_id, name=name, data=data,
                                        is_blocked=True)
    assert device.id == device_id
    assert device.name == name
    assert device.data == data
    assert isinstance(device.network_id, int)
    assert isinstance(device.device_type_id, int)
    assert device.is_blocked
    device.remove()


def test_list_networks(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()
    test_id, network_ids = test.generate_ids('l-n', test.NETWORK_ENTITY, 2)
    options = [{'name': network_id,
                'description': '%s-description' % network_id}
               for network_id in network_ids]
    test_networks = [device_hive_api.create_network(**option)
                     for option in options]
    networks = device_hive_api.list_networks()
    assert len(networks) >= len(options)
    name = options[0]['name']
    network, = device_hive_api.list_networks(name=name)
    assert network.name == name
    name_pattern = test.generate_id('l-n-n-e')
    assert not device_hive_api.list_networks(name_pattern=name_pattern)
    name_pattern = test_id + '%'
    networks = device_hive_api.list_networks(name_pattern=name_pattern)
    assert len(networks) == len(options)
    network_0, network_1 = device_hive_api.list_networks(
            name_pattern=name_pattern, sort_field='name', sort_order='ASC')
    assert network_0.name == options[0]['name']
    assert network_1.name == options[1]['name']
    network_0, network_1 = device_hive_api.list_networks(
            name_pattern=name_pattern, sort_field='name', sort_order='DESC')
    assert network_0.name == options[1]['name']
    assert network_1.name == options[0]['name']
    network, = device_hive_api.list_networks(name_pattern=name_pattern,
                                             sort_field='name',
                                             sort_order='ASC', take=1)
    assert network.name == options[0]['name']
    network, = device_hive_api.list_networks(name_pattern=name_pattern,
                                             sort_field='name',
                                             sort_order='ASC', take=1,
                                             skip=1)
    assert network.name == options[1]['name']
    [test_network.remove() for test_network in test_networks]


def test_get_network(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()
    name = test.generate_id('g-n', test.NETWORK_ENTITY)
    description = '%s-description' % name
    network = device_hive_api.create_network(name, description)
    network = device_hive_api.get_network(network.id)
    assert isinstance(network.id, int)
    assert network.name == name
    assert network.description == description
    network_id = network.id
    network.remove()
    try:
        device_hive_api.get_network(network_id)
        assert False
    except ApiResponseError as api_response_error:
        assert api_response_error.code == 404


def test_create_network(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()
    name = test.generate_id('c-n', test.NETWORK_ENTITY)
    description = '%s-description' % name
    network = device_hive_api.create_network(name, description)
    assert isinstance(network.id, int)
    assert network.name == name
    assert network.description == description
    try:
        device_hive_api.create_network(name, description)
        assert False
    except ApiResponseError as api_response_error:
        assert api_response_error.code == 403
    network.remove()


def test_list_device_types(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()
    test_id, device_type_ids = test.generate_ids('l-dt',
                                                 test.DEVICE_TYPE_ENTITY, 2)
    options = [{'name': device_type_id,
                'description': '%s-description' % device_type_id}
               for device_type_id in device_type_ids]
    test_device_types = [device_hive_api.create_device_type(**option)
                         for option in options]
    device_types = device_hive_api.list_device_types()
    assert len(device_types) >= len(options)
    name = options[0]['name']
    device_type, = device_hive_api.list_device_types(name=name)
    assert device_type.name == name
    name_pattern = test.generate_id('l-dt-n-e')
    assert not device_hive_api.list_device_types(name_pattern=name_pattern)
    name_pattern = test_id + '%'
    device_types = device_hive_api.list_device_types(name_pattern=name_pattern)
    assert len(device_types) == len(options)
    device_type_0, device_type_1 = device_hive_api.list_device_types(
        name_pattern=name_pattern, sort_field='name', sort_order='ASC')
    assert device_type_0.name == options[0]['name']
    assert device_type_1.name == options[1]['name']
    device_type_0, device_type_1 = device_hive_api.list_device_types(
        name_pattern=name_pattern, sort_field='name', sort_order='DESC')
    assert device_type_0.name == options[1]['name']
    assert device_type_1.name == options[0]['name']
    device_type, = device_hive_api.list_device_types(name_pattern=name_pattern,
                                                     sort_field='name',
                                                     sort_order='ASC', take=1)
    assert device_type.name == options[0]['name']
    device_type, = device_hive_api.list_device_types(name_pattern=name_pattern,
                                                     sort_field='name',
                                                     sort_order='ASC', take=1,
                                                     skip=1)
    assert device_type.name == options[1]['name']
    [test_device_type.remove() for test_device_type in test_device_types]


def test_get_device_type(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()
    name = test.generate_id('g-dt', test.DEVICE_TYPE_ENTITY)
    description = '%s-description' % name
    device_type = device_hive_api.create_device_type(name, description)
    device_type = device_hive_api.get_device_type(device_type.id)
    assert isinstance(device_type.id, int)
    assert device_type.name == name
    assert device_type.description == description
    device_type_id = device_type.id
    device_type.remove()
    try:
        device_hive_api.get_device_type(device_type_id)
        assert False
    except ApiResponseError as api_response_error:
        assert api_response_error.code == 404


def test_create_device_type(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()
    name = test.generate_id('c-dt', test.DEVICE_TYPE_ENTITY)
    description = '%s-description' % name
    device_type = device_hive_api.create_device_type(name, description)
    assert isinstance(device_type.id, int)
    assert device_type.name == name
    assert device_type.description == description
    try:
        device_hive_api.create_device_type(name, description)
        assert False
    except ApiResponseError as api_response_error:
        assert api_response_error.code == 403
    device_type.remove()


def test_list_users(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()
    test_id, user_ids = test.generate_ids('l-u', test.USER_ENTITY, 2)
    role = User.ADMINISTRATOR_ROLE
    options = [{'login': user_id,
                'password': '%s-password' % user_id,
                'role': role, 'data': {str(i): i}}
               for i, user_id in enumerate(user_ids)]
    test_users = [device_hive_api.create_user(**option) for option in options]
    users = device_hive_api.list_users()
    assert len(users) >= len(options)
    login = options[0]['login']
    user, = device_hive_api.list_users(login=login)
    assert user.login == login
    login_pattern = test.generate_id('l-u-n-e')
    assert not device_hive_api.list_users(login_pattern=login_pattern)
    login_pattern = test_id + '%'
    users = device_hive_api.list_users(login_pattern=login_pattern)
    assert len(users) == len(options)
    users = device_hive_api.list_users(role=role)
    assert len(users) >= len(options)
    status = User.ACTIVE_STATUS
    users = device_hive_api.list_users(status=status)
    assert len(users) >= len(options)
    user_0, user_1 = device_hive_api.list_users(login_pattern=login_pattern,
                                                sort_field='login',
                                                sort_order='ASC')
    assert user_0.login == options[0]['login']
    assert user_1.login == options[1]['login']
    user_0, user_1 = device_hive_api.list_users(login_pattern=login_pattern,
                                                sort_field='login',
                                                sort_order='DESC')
    assert user_0.login == options[1]['login']
    assert user_1.login == options[0]['login']
    user, = device_hive_api.list_users(login_pattern=login_pattern,
                                       sort_field='login', sort_order='ASC',
                                       take=1)
    assert user.login == options[0]['login']
    user, = device_hive_api.list_users(login_pattern=login_pattern,
                                       sort_field='login', sort_order='ASC',
                                       take=1, skip=1)
    assert user.login == options[1]['login']
    [test_user.remove() for test_user in test_users]


def test_get_current_user(test):
    device_hive_api = test.device_hive_api()
    user = device_hive_api.get_current_user()
    assert isinstance(user.id, int)


def test_get_user(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()
    login = test.generate_id('g-u', test.USER_ENTITY)
    password = test.generate_id('g-u')
    role = User.ADMINISTRATOR_ROLE
    data = {'k': 'v'}
    user = device_hive_api.create_user(login, password, role, data)
    user = device_hive_api.get_user(user.id)
    assert isinstance(user.id, int)
    assert user.login == login
    assert not user.last_login
    assert not user.intro_reviewed
    assert user.role == role
    assert user.status == User.ACTIVE_STATUS
    assert user.data == data
    user_id = user.id
    user.remove()
    try:
        device_hive_api.get_user(user_id)
        assert False
    except ApiResponseError as api_response_error:
        assert api_response_error.code == 404


def test_create_user(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()
    login = test.generate_id('c-u', test.USER_ENTITY)
    password = test.generate_id('c-u')
    role = User.ADMINISTRATOR_ROLE
    data = {'k': 'v'}
    user = device_hive_api.create_user(login, password, role, data)
    assert isinstance(user.id, int)
    assert user.login == login
    assert not user.last_login
    assert not user.intro_reviewed
    assert user.role == role
    assert user.status == User.ACTIVE_STATUS
    assert user.data == data
    try:
        device_hive_api.create_user(login, password, role, data)
        assert False
    except ApiResponseError as api_response_error:
        assert api_response_error.code == 403
    user.remove()
