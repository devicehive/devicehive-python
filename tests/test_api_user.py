from devicehive.user import User
from devicehive import UserError
from devicehive import ApiResponseError


def test_save(test):

    def handle_connect(handler):
        login = test.generate_id('c-u')
        password = test.generate_id('c-u')
        role = User.ADMINISTRATOR_ROLE
        data = {'k': 'v'}
        user = handler.api.create_user(login, password, role, data)
        role = User.CLIENT_ROLE
        status = User.DISABLED_STATUS
        data = {'k-1': 'v-1'}
        user.role = role
        user.status = status
        user.data = data
        user.save()
        user = handler.api.get_user(user.id)
        assert user.role == role
        assert user.status == status
        assert user.data == data
        user.remove()
        try:
            user.save()
            assert False
        except UserError:
            pass

    test.run(handle_connect)


def test_remove(test):

    def handle_connect(handler):
        login = test.generate_id('c-u')
        password = test.generate_id('c-u')
        role = User.ADMINISTRATOR_ROLE
        data = {'k': 'v'}
        user = handler.api.create_user(login, password, role, data)
        user_1 = handler.api.get_user(user.id)
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
            # TODO: uncomment after server response will be fixed.
            # assert api_response_error.code == 404
            pass

    test.run(handle_connect)
