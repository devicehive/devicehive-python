from devicehive.handler import Handler
from devicehive.device_hive import DeviceHive


class ApiCallHandler(Handler):
    """Api call handler class."""

    def __init__(self, api, call, *call_args, **call_kwargs):
        super(ApiCallHandler, self).__init__(api)
        self._call = call
        self._call_args = call_args
        self._call_kwargs = call_kwargs
        self._call_result = None

    @property
    def call_result(self):
        return self._call_result

    def handle_connect(self):
        self._call_result = getattr(self.api, self._call)(*self._call_args,
                                                          **self._call_kwargs)
        self.api.disconnect()


class DeviceHiveApi(object):
    """Device hive api class."""

    def __init__(self, transport_url, **options):
        self._transport_url = transport_url
        self._options = options

    def _call(self, call, *call_args, **call_kwargs):
        device_hive = DeviceHive(ApiCallHandler, call, *call_args,
                                 **call_kwargs)
        device_hive.connect(self._transport_url, **self._options)
        return device_hive.transport.handler.handler.call_result

    def get_info(self):
        return self._call('get_info')

    def get_cluster_info(self):
        return self._call('get_cluster_info')
