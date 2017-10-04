from devicehive import NetworkError
from devicehive import ApiResponseError


def test_save(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()
    name = test.generate_id('n-s')
    description = '%s-description' % name
    network = device_hive_api.create_network(name, description)
    name = test.generate_id('n-s')
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
        # TODO: uncomment after server response will be fixed.
        # assert api_response_error.code == 404
        pass


def test_remove(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()
    name = test.generate_id('n-r')
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
