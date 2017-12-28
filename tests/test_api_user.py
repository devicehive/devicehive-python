from devicehive.user import User
from devicehive import UserError
from devicehive import ApiResponseError


def test_save(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()
    login = test.generate_id('u-s', test.USER_ENTITY)
    password = test.generate_id('u-s')
    role = User.ADMINISTRATOR_ROLE
    data = {'k': 'v'}
    user = device_hive_api.create_user(login, password, role, data)
    role = User.CLIENT_ROLE
    status = User.DISABLED_STATUS
    all_device_types_available = True
    data = {'k-1': 'v-1'}
    user.role = role
    user.status = status
    user.data = data
    user.save()
    user = device_hive_api.get_user(user.id)
    assert user.role == role
    assert user.status == status
    assert user.data == data
    assert user.all_device_types_available == all_device_types_available
    user.remove()
    try:
        user.save()
        assert False
    except UserError:
        pass


def test_update_password(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()
    login = test.generate_id('u-u-p', test.USER_ENTITY)
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
    login = test.generate_id('u-r', test.USER_ENTITY)
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
    login = test.generate_id('u-l-n', test.USER_ENTITY)
    password = test.generate_id('u-l-n')
    role = User.ADMINISTRATOR_ROLE
    data = {'k': 'v'}
    user = device_hive_api.create_user(login, password, role, data)
    networks = user.list_networks()
    assert networks == []
    network_name = test.generate_id('u-l-n', test.NETWORK_ENTITY)
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
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()
    login = test.generate_id('u-a-n', test.USER_ENTITY)
    password = test.generate_id('u-a-n')
    role = User.ADMINISTRATOR_ROLE
    data = {'k': 'v'}
    user = device_hive_api.create_user(login, password, role, data)
    networks = user.list_networks()
    assert networks == []
    network_name = test.generate_id('u-a-n', test.NETWORK_ENTITY)
    network_description = '%s-description' % network_name
    network = device_hive_api.create_network(network_name, network_description)
    user.assign_network(network.id)
    network, = user.list_networks()
    assert network.name == network_name
    assert network.description == network_description
    user_1 = device_hive_api.get_user(user.id)
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


def test_unassign_network(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()
    login = test.generate_id('u-u-n', test.USER_ENTITY)
    password = test.generate_id('u-u-n')
    role = User.ADMINISTRATOR_ROLE
    data = {'k': 'v'}
    user = device_hive_api.create_user(login, password, role, data)
    networks = user.list_networks()
    assert networks == []
    network_name = test.generate_id('u-u-n', test.NETWORK_ENTITY)
    network_description = '%s-description' % network_name
    network = device_hive_api.create_network(network_name, network_description)
    user.assign_network(network.id)
    user.unassign_network(network.id)
    networks = user.list_networks()
    assert networks == []
    user_1 = device_hive_api.get_user(user.id)
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


def test_list_device_types(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()
    login = test.generate_id('u-l-dt', test.USER_ENTITY)
    password = test.generate_id('u-l-dt')
    role = User.ADMINISTRATOR_ROLE
    data = {'k': 'v'}
    all_device_types_available = False
    user = device_hive_api.create_user(login, password, role, data,
                                       all_device_types_available)
    device_types = user.list_device_types()
    assert device_types == []
    device_type_name = test.generate_id('u-l-dt', test.DEVICE_TYPE_ENTITY)
    device_type_description = '%s-description' % device_type_name
    device_type = device_hive_api.create_device_type(device_type_name,
                                                     device_type_description)
    user.assign_device_type(device_type.id)
    device_type, = user.list_device_types()
    assert device_type.name == device_type_name
    assert device_type.description == device_type_description
    user_1 = device_hive_api.get_user(user.id)
    user.remove()
    device_type.remove()
    try:
        user.list_device_types()
        assert False
    except UserError:
        pass
    try:
        user_1.list_device_types()
        assert False
    except ApiResponseError as api_response_error:
        assert api_response_error.code == 404


def test_assign_all_device_types(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()

    device_type_name = test.generate_id('u-a-a-dt', test.DEVICE_TYPE_ENTITY)
    device_type_description = '%s-description' % device_type_name
    device_hive_api.create_device_type(device_type_name,
                                       device_type_description)

    login = test.generate_id('u-a-a-dt', test.USER_ENTITY)
    password = test.generate_id('u-a-a-dt')
    role = User.ADMINISTRATOR_ROLE
    data = {'k': 'v'}
    all_device_types_available = False
    user = device_hive_api.create_user(login, password, role, data,
                                       all_device_types_available)
    user_1 = device_hive_api.get_user(user.id)

    device_types = user.list_device_types()
    assert device_types == []
    user.allow_all_device_types()
    device_types = user.list_device_types()
    assert device_types != []

    try:
        user.allow_all_device_types()
        assert False
    except UserError:
        pass

    user.remove()

    try:
        user.allow_all_device_types()
        assert False
    except UserError:
        pass

    try:
        user_1.allow_all_device_types()
        assert False
    except ApiResponseError as api_response_error:
        assert api_response_error.code == 404


def test_unassign_all_device_types(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()

    device_type_name = test.generate_id('u-u-a-dt', test.DEVICE_TYPE_ENTITY)
    device_type_description = '%s-description' % device_type_name
    device_hive_api.create_device_type(device_type_name,
                                       device_type_description)

    login = test.generate_id('u-u-a-dt', test.USER_ENTITY)
    password = test.generate_id('u-u-a-dt')
    role = User.ADMINISTRATOR_ROLE
    data = {'k': 'v'}
    all_device_types_available = True
    user = device_hive_api.create_user(login, password, role, data,
                                       all_device_types_available)
    user_1 = device_hive_api.get_user(user.id)

    device_types = user.list_device_types()
    assert device_types != []
    user.disallow_all_device_types()
    device_types = user.list_device_types()
    assert device_types == []

    try:
        user.disallow_all_device_types()
        assert False
    except UserError:
        pass

    user.remove()

    try:
        user.disallow_all_device_types()
        assert False
    except UserError:
        pass

    try:
        user_1.disallow_all_device_types()
        assert False
    except ApiResponseError as api_response_error:
        assert api_response_error.code == 404


def test_assign_device_type(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()

    device_type_name = test.generate_id('u-a-dt', test.DEVICE_TYPE_ENTITY)
    device_type_description = '%s-description' % device_type_name
    device_type = device_hive_api.create_device_type(device_type_name,
                                                     device_type_description)

    login = test.generate_id('u-a-dt', test.USER_ENTITY)
    password = test.generate_id('u-a-dt')
    role = User.ADMINISTRATOR_ROLE
    data = {'k': 'v'}
    all_device_types_available = False
    user = device_hive_api.create_user(login, password, role, data,
                                       all_device_types_available)
    device_types = user.list_device_types()
    assert device_types == []

    user_1 = device_hive_api.get_user(user.id)
    user.allow_all_device_types()

    try:
        user.assign_device_type(device_type.id)
        assert False
    except UserError:
        pass

    try:
        user_1.assign_device_type(device_type.id)
        assert False
    except ApiResponseError as api_response_error:
        assert api_response_error.code == 403

    user.disallow_all_device_types()

    user.assign_device_type(device_type.id)
    device_type, = user.list_device_types()
    assert device_type.name == device_type_name
    assert device_type.description == device_type_description
    user_1 = device_hive_api.get_user(user.id)
    user.remove()
    try:
        user.assign_device_type(device_type.id)
        assert False
    except UserError:
        pass
    try:
        user_1.assign_device_type(device_type.id)
        assert False
    except ApiResponseError as api_response_error:
        assert api_response_error.code == 404
    device_type.remove()


def test_unassign_device_type(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()

    device_type_name = test.generate_id('u-u-dt', test.DEVICE_TYPE_ENTITY)
    device_type_description = '%s-description' % device_type_name
    device_type = device_hive_api.create_device_type(device_type_name,
                                                     device_type_description)

    login = test.generate_id('u-u-dt', test.USER_ENTITY)
    password = test.generate_id('u-u-dt')
    role = User.ADMINISTRATOR_ROLE
    data = {'k': 'v'}
    all_device_types_available = False
    user = device_hive_api.create_user(login, password, role, data,
                                       all_device_types_available)
    device_types = user.list_device_types()
    assert device_types == []

    user_1 = device_hive_api.get_user(user.id)
    user.allow_all_device_types()

    try:
        user.unassign_device_type(device_type.id)
        assert False
    except UserError:
        pass

    try:
        user_1.unassign_device_type(device_type.id)
        assert False
    except ApiResponseError as api_response_error:
        assert api_response_error.code == 403

    user.disallow_all_device_types()

    user.assign_device_type(device_type.id)
    user.unassign_device_type(device_type.id)
    device_types = user.list_device_types()
    assert device_types == []
    user_1 = device_hive_api.get_user(user.id)
    user.remove()
    try:
        user.unassign_device_type(device_type.id)
        assert False
    except UserError:
        pass
    try:
        user_1.unassign_device_type(device_type.id)
        assert False
    except ApiResponseError as api_response_error:
        assert api_response_error.code == 404
    device_type.remove()
