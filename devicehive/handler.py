class Handler(object):
    """Handler class."""

    def __init__(self, api, options):
        self.api = api
        self.options = options

    def handle_connect(self):
        raise NotImplementedError

    def handle_event(self, event):
        raise NotImplementedError
