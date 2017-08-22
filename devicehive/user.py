from devicehive.api_request import AuthApiRequest
from devicehive.api_request import ApiRequestError
from devicehive.network import Network


class User(object):
    """User class."""

    ID_KEY = 'id'
    LOGIN_KEY = 'login'
    LAST_LOGIN_KEY = 'lastLogin'
    INTRO_REVIEWED_KEY = 'introReviewed'
    ROLE_KEY = 'role'
    STATUS_KEY = 'status'
    DATA_KEY = 'data'
    PASSWORD_KEY = 'password'
    NETWORKS_KEY = 'networks'
    ADMINISTRATOR_ROLE = 0
    CLIENT_ROLE = 1
    ACTIVE_STATUS = 0
    LOCKED_STATUS = 1
    DISABLED_STATUS = 2

    def __init__(self, api, user=None):
        self._api = api
        self._id = None
        self._login = None
        self._last_login = None
        self._intro_reviewed = None
        self.role = None
        self.status = None
        self.data = None

        if user:
            self._init(user)

    def _init(self, user):
        self._id = user[self.ID_KEY]
        self._login = user[self.LOGIN_KEY]
        self._last_login = user[self.LAST_LOGIN_KEY]
        self._intro_reviewed = user[self.INTRO_REVIEWED_KEY]
        self.role = user[self.ROLE_KEY]
        self.status = user[self.STATUS_KEY]
        self.data = user[self.DATA_KEY]

    def _ensure_exists(self):
        if self._id:
            return
        raise UserError('User does not exist.')

    @property
    def id(self):
        return self._id

    @property
    def login(self):
        return self._login

    @property
    def last_login(self):
        return self._last_login

    @property
    def intro_reviewed(self):
        return self._intro_reviewed

    def get_current(self):
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.url('user/current')
        auth_api_request.action('user/getCurrent')
        auth_api_request.response_key('current')
        user = auth_api_request.execute('Current user get failure.')
        self._init(user)

    def get(self, user_id):
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.url('user/{userId}', userId=user_id)
        auth_api_request.action('user/get')
        auth_api_request.response_key('user')
        user = auth_api_request.execute('User get failure.')
        self._init(user)

    def save(self):
        self._ensure_exists()
        user = {self.ROLE_KEY: self.role,
                self.STATUS_KEY: self.status,
                self.DATA_KEY: self.data}
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.method('PUT')
        auth_api_request.url('user/{userId}', userId=self._id)
        auth_api_request.action('user/update')
        auth_api_request.set('user', user, True)
        auth_api_request.execute('User save failure.')

    def update_password(self, password):
        self._ensure_exists()
        user = {self.PASSWORD_KEY: password}
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.method('PUT')
        auth_api_request.url('user/{userId}', userId=self._id)
        auth_api_request.action('user/update')
        auth_api_request.set('user', user, True)
        auth_api_request.execute('User password update failure.')

    def remove(self):
        self._ensure_exists()
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.method('DELETE')
        auth_api_request.url('user/{userId}', userId=self._id)
        auth_api_request.action('user/delete')
        auth_api_request.execute('User remove failure.')
        self._id = None
        self._login = None
        self._last_login = None
        self._intro_reviewed = None
        self.role = None
        self.status = None
        self.data = None

    def list_networks(self):
        self._ensure_exists()
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.url('user/{userId}', userId=self._id)
        auth_api_request.action('user/get')
        auth_api_request.response_key('user')
        user = auth_api_request.execute('List networks failure.')
        return [Network(self._api, network)
                for network in user[User.NETWORKS_KEY]]

    def assign_network(self, network_id):
        self._ensure_exists()
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.method('PUT')
        auth_api_request.url('user/{userId}/network/{networkId}',
                             userId=self._id, networkId=network_id)
        auth_api_request.action('user/assignNetwork')
        auth_api_request.execute('Assign network failure.')

    def unassign_network(self, network_id):
        self._ensure_exists()
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.method('DELETE')
        auth_api_request.url('user/{userId}/network/{networkId}',
                             userId=self._id, networkId=network_id)
        auth_api_request.action('user/unassignNetwork')
        auth_api_request.execute('Unassign network failure.')


class UserError(ApiRequestError):
    """User error."""
