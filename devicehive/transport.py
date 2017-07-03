def init(name, data_format, data_format_options, handler, handler_options):
    transport_class_name = '%sTransport' % name.title()
    transport_module = __import__('devicehive.transports.%s_transport' % name,
                                  fromlist=[transport_class_name])
    return getattr(transport_module, transport_class_name)(data_format,
                                                           data_format_options,
                                                           handler,
                                                           handler_options)


class Request(object):
    """Request class."""

    def __init__(self, url, action, request, **params):
        self._action = action
        self._request = request
        self._params = params
        self._params['url'] = url

    def action(self):
        return self._action

    def request(self):
        return self._request

    def params(self):
        return self._params


class Response(object):
    """Response class."""

    def __init__(self, response):
        self._id = response.pop('requestId')
        self._action = response.pop('action')
        self._is_success = response.pop('status') == 'success'
        self._code = response.pop('code', None)
        self._error = response.pop('error', None)
        self._data = response

    def id(self):
        return self._id

    def action(self):
        return self._action

    def is_success(self):
        return self._is_success

    def code(self):
        return self._code

    def error(self):
        return self._error

    def data(self):
        return self._data
