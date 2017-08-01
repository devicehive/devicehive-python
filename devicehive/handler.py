import warnings


class Handler(object):
    """Handler class."""

    def __init__(self, api):
        self._api = api

    @property
    def api(self):
        return self._api

    def handle_connect(self):
        raise NotImplementedError

    def handle_command_insert(self, subscription_id, command):
        message = 'Inserted command received. Subscription id: %s.'
        message %= subscription_id
        warnings.warn(message, HandlerWarning)

    def handle_command_update(self, subscription_id, command):
        message = 'Updated command received. Subscription id: %s.'
        message %= subscription_id
        warnings.warn(message, HandlerWarning)

    def handle_notification_insert(self, subscription_id, notification):
        message = 'Inserted notification received. Subscription id: %s.'
        message %= subscription_id
        warnings.warn(message, HandlerWarning)


class HandlerWarning(UserWarning):
    """Handler warning."""
