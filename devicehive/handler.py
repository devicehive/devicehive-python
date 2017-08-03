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

    def handle_command_insert(self, command):
        message = 'Inserted command received. Command id: %s.' % command.id
        warnings.warn(message, HandlerWarning)

    def handle_command_update(self, command):
        message = 'Updated command received. Command id: %s.' % command.id
        warnings.warn(message, HandlerWarning)

    def handle_notification(self, notification):
        message = 'Notification received. Notification id: %s.'
        message %= notification.id
        warnings.warn(message, HandlerWarning)


class HandlerWarning(UserWarning):
    """Handler warning."""
