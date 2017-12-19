from devicehive import DeviceTypeError
from devicehive import ApiResponseError


def test_save(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()
    name = test.generate_id('dt-s', test.DEVICE_TYPE_ENTITY)
    description = '%s-description' % name
    device_type = device_hive_api.create_device_type(name, description)
    name = test.generate_id('dt-s', test.DEVICE_TYPE_ENTITY)
    description = '%s-description' % name
    device_type.name = name
    device_type.description = description
    device_type.save()
    device_type_1 = device_hive_api.get_device_type(device_type.id)
    device_type.remove()
    try:
        device_type.save()
        assert False
    except DeviceTypeError:
        pass
    try:
        device_type_1.save()
        assert False
    except ApiResponseError as api_response_error:
        # TODO: uncomment after server response will be fixed.
        # assert api_response_error.code == 404
        pass


def test_remove(test):
    test.only_admin_implementation()
    device_hive_api = test.device_hive_api()
    name = test.generate_id('dt-r', test.DEVICE_TYPE_ENTITY)
    description = '%s-description' % name
    device_type = device_hive_api.create_device_type(name, description)
    device_type_1 = device_hive_api.get_device_type(device_type.id)
    device_type.remove()
    assert not device_type.id
    assert not device_type.name
    assert not device_type.description
    try:
        device_type.remove()
        assert False
    except DeviceTypeError:
        pass
    try:
        device_type_1.remove()
        assert False
    except ApiResponseError as api_response_error:
        assert api_response_error.code == 404
