class ApiEvent(object):
    """Api event class."""

    EVENT_ACTION_KEY = 'action'
    EVENT_SUBSCRIPTION_ID_KEY = 'subscriptionId'

    def __init__(self, event):
        self._action = event.pop(self.EVENT_ACTION_KEY)
        self._subscription_id = event.pop(self.EVENT_SUBSCRIPTION_ID_KEY)
        self._event = event

    @property
    def action(self):
        return self._action

    @property
    def subscription_id(self):
        return self._subscription_id

    @property
    def event(self):
        return self._event
