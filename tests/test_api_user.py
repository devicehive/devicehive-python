from devicehive.user import User
from devicehive import UserError
from devicehive import ApiResponseError


def test_save(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()
    login = test.generate_id('u-s')
    password = test.generate_id('u-s')
    role = User.ADMINISTRATOR_ROLE
    data = {'k': 'v'}
    user = device_hive_api.create_user(login, password, role, data)
    role = User.CLIENT_ROLE
    status = User.DISABLED_STATUS
    data = {'k-1': 'v-1'}
    user.role = role
    user.status = status
    user.data = data
    user.save()
    user = device_hive_api.get_user(user.id)
    assert user.role == role
    assert user.status == status
    assert user.data == data
    user.remove()
    try:
        user.save()
        assert False
    except UserError:
        pass


def test_update_password(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()
    login = test.generate_id('u-u-p')
    password = test.generate_id('u-u-p')
    role = User.ADMINISTRATOR_ROLE
    data = {'k': 'v'}
    user = device_hive_api.create_user(login, password, role, data)
    password_1 = test.generate_id('u-u-p')
    user.update_password(password_1)
    user_1 = device_hive_api.get_user(user.id)
    user.remove()
    try:
        user.update_password(password_1)
        assert False
    except UserError:
        pass
    try:
        user_1.update_password(password_1)
        assert False
    except ApiResponseError as api_response_error:
        assert api_response_error.code == 404


def test_remove(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()
    login = test.generate_id('u-r')
    password = test.generate_id('u-r')
    role = User.ADMINISTRATOR_ROLE
    data = {'k': 'v'}
    user = device_hive_api.create_user(login, password, role, data)
    user_1 = device_hive_api.get_user(user.id)
    user.remove()
    assert not user.id
    assert not user.login
    assert not user.last_login
    assert not user.intro_reviewed
    assert not user.role
    assert not user.status
    assert not user.data
    try:
        user.remove()
        assert False
    except UserError:
        pass
    try:
        user_1.remove()
        assert False
    except ApiResponseError as api_response_error:
        assert api_response_error.code == 404


def test_list_networks(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()
    login = test.generate_id('u-l-n')
    password = test.generate_id('u-l-n')
    role = User.ADMINISTRATOR_ROLE
    data = {'k': 'v'}
    user = device_hive_api.create_user(login, password, role, data)
    networks = user.list_networks()
    assert networks == []
    network_name = test.generate_id('u-l-n')
    network_description = '%s-description' % network_name
    network = device_hive_api.create_network(network_name, network_description)
    user.assign_network(network.id)
    network, = user.list_networks()
    assert network.name == network_name
    assert network.description == network_description
    user_1 = device_hive_api.get_user(user.id)
    user.remove()
    network.remove()
    try:
        user.list_networks()
        assert False
    except UserError:
        pass
    try:
        user_1.list_networks()
        assert False
    except ApiResponseError as api_response_error:
        assert api_response_error.code == 404


def test_assign_network(test):

    def handle_connect(handler):
        login = test.generate_id('u-a-n')
        password = test.generate_id('u-a-n')
        role = User.ADMINISTRATOR_ROLE
        data = {'k': 'v'}
        user = handler.api.create_user(login, password, role, data)
        networks = user.list_networks()
        assert networks == []
        network_name = test.generate_id('u-a-n')
        network_description = '%s-description' % network_name
        network = handler.api.create_network(network_name, network_description)
        user.assign_network(network.id)
        network, = user.list_networks()
        assert network.name == network_name
        assert network.description == network_description
        user_1 = handler.api.get_user(user.id)
        user.remove()
        try:
            user.assign_network(network.id)
            assert False
        except UserError:
            pass
        try:
            user_1.assign_network(network.id)
            assert False
        except ApiResponseError as api_response_error:
            assert api_response_error.code == 404
        network.remove()

    test.only_admin_implementation()
    test.run(handle_connect)


def test_unassign_network(test):

    def handle_connect(handler):
        login = test.generate_id('u-u-n')
        password = test.generate_id('u-u-n')
        role = User.ADMINISTRATOR_ROLE
        data = {'k': 'v'}
        user = handler.api.create_user(login, password, role, data)
        networks = user.list_networks()
        assert networks == []
        network_name = test.generate_id('u-u-n')
        network_description = '%s-description' % network_name
        network = handler.api.create_network(network_name, network_description)
        user.assign_network(network.id)
        user.unassign_network(network.id)
        networks = user.list_networks()
        assert networks == []
        user_1 = handler.api.get_user(user.id)
        user.remove()
        try:
            user.unassign_network(network.id)
            assert False
        except UserError:
            pass
        try:
            user_1.unassign_network(network.id)
            assert False
        except ApiResponseError as api_response_error:
            assert api_response_error.code == 404
        network.remove()

    test.only_admin_implementation()
    test.run(handle_connect)
