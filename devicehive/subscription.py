# Copyright (C) 2018 DataArt
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================


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
