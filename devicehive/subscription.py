from devicehive.api_request import RemoveSubscriptionApiRequest, ApiRequest, \
    ApiRequestError


class BaseSubscription(object):
    """BaseSubscription class"""

    ID_KEY = 'subscriptionId'

    def __init__(self, api, subscription=None):
        self._api = api
        self._id = None

        if subscription:
            self._init(subscription)

    def _init(self, subscription):
        self._id = subscription[self.ID_KEY]

    def _ensure_exists(self):
        if self._id:
            return
        raise SubscriptionError('Subscription does not exist.')

    @property
    def id(self):
        return self._id

    def _get_subscription_type(self):
        raise NotImplementedError

    def remove(self):
        self._ensure_exists()
        remove_subscription_api_request = RemoveSubscriptionApiRequest()
        remove_subscription_api_request.subscription_id(self._id)
        api_request = ApiRequest(self._api)
        api_request.action('%s/unsubscribe' % self._get_subscription_type())
        api_request.set('subscriptionId', self._id)
        api_request.remove_subscription_request(remove_subscription_api_request)
        api_request.execute('Unsubscribe failure.')
        self._id = None


class CommandsSubscription(BaseSubscription):
    """CommandsSubscription class"""

    def _get_subscription_type(self):
        return 'command'


class NotificationsSubscription(BaseSubscription):
    """NotificationsSubscription class"""

    def _get_subscription_type(self):
        return 'notification'


class SubscriptionError(ApiRequestError):
    """Subscription error."""
