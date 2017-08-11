from devicehive.api_request import AuthApiRequest
from devicehive.api_request import ApiRequestError


class User(object):
    """User class."""

    ID_KEY = 'id'
    LOGIN_KEY = 'login'
    LAST_LOGIN_KEY = 'lastLogin'
    INTRO_REVIEWED_KEY = 'introReviewed'
    NETWORKS_KEY = 'networks'
    ROLE_KEY = 'role'
    STATUS_KEY = 'status'
    DATA_KEY = 'data'
    PASSWORD_KEY = 'password'
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
        self._networks = []
        self.role = None
        self.status = None
        self.data = None
        self.password = None

        if user:
            self._init(user)

    def _init(self, user):
        self._id = user[self.ID_KEY]
        self._login = user[self.LOGIN_KEY]
        self._last_login = user[self.LAST_LOGIN_KEY]
        self._intro_reviewed = user[self.INTRO_REVIEWED_KEY]
        networks = user.get(self.NETWORKS_KEY)
        if networks:
            self._networks = networks
        self.role = user[self.ROLE_KEY]
        self.status = user[self.STATUS_KEY]
        self.data = user[self.DATA_KEY]
        password = user.get(self.PASSWORD_KEY)
        if password:
            self.password = password

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

    @property
    def networks(self):
        return self._networks

    def get(self, user_id):
        auth_api_request = AuthApiRequest(self._api)
        auth_api_request.url('user/{userId}', userId=user_id)
        auth_api_request.action('user/get')
        auth_api_request.response_key('user')
        user = auth_api_request.execute('User get failure.')
        self._init(user)


class UserError(ApiRequestError):
    """User error."""
