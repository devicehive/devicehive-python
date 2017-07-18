class Notification(object):
    """Notification class."""

    DEVICE_ID_KEY = 'deviceId'
    ID_KEY = 'id'
    NOTIFICATION_KEY = 'notification'
    PARAMETERS_KEY = 'parameters'
    TIMESTAMP_KEY = 'timestamp'

    def __init__(self, notification):
        self._device_id = notification[self.DEVICE_ID_KEY]
        self._id = notification[self.ID_KEY]
        self._notification = notification[self.NOTIFICATION_KEY]
        self._parameters = notification[self.PARAMETERS_KEY]
        self._timestamp = notification[self.TIMESTAMP_KEY]

    def device_id(self):
        return self._device_id

    def id(self):
        return self._id

    def notification(self):
        return self._notification

    def parameters(self):
        return self._parameters

    def timestamp(self):
        return self._timestamp
