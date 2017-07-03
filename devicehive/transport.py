def init(name, data_format_class, data_format_options, handler_class,
         handler_options):
    transport_class_name = '%sTransport' % name.title()
    transport_module = __import__('devicehive.transports.%s_transport' % name,
                                  fromlist=[transport_class_name])
    return getattr(transport_module, transport_class_name)(data_format_class,
                                                           data_format_options,
                                                           handler_class,
                                                           handler_options)


class Request(object):
    """Request class."""

    def __init__(self, url, action, request, **params):
        self.action = action
        self.request = request
        self.params = params
        self.params['url'] = url


class Response(object):
    """Response class."""

    def __init__(self, response):
        self.id = response.pop('requestId')
        self.action = response.pop('action')
        self.is_success = response.pop('status') == 'success'
        self.code = response.pop('code', None)
        self.error = response.pop('error', None)
        self.data = response
