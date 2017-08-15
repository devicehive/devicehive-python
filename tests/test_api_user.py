from devicehive.user import User
from devicehive import UserError


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
