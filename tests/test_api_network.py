from devicehive import NetworkError
from devicehive import ApiResponseError


def test_save(test):

    def handle_connect(handler):
        name = test.generate_id('n-s')
        description = '%s-description' % name
        network = handler.api.create_network(name, description)
        name = test.generate_id('n-s')
        description = '%s-description' % name
        network.name = name
        network.description = description
        network.save()
        network_1 = handler.api.get_network(network.id)
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

    test.run(handle_connect)


def test_remove(test):

    def handle_connect(handler):
        name = test.generate_id('n-r')
        description = '%s-description' % name
        network = handler.api.create_network(name, description)
        network_1 = handler.api.get_network(network.id)
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
            # TODO: uncomment after server response will be fixed.
            # assert api_response_error.code == 404
            pass

    test.run(handle_connect)
