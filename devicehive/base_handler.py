class BaseHandler(object):

    def __init__(self, api, options):
        self.api = api
        self.options = options

    def handle_connected(self):
        raise NotImplementedError

    def handle_event(self, event):
        raise NotImplementedError
