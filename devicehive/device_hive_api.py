from devicehive.handler import Handler
from devicehive.device_hive import DeviceHive
import time
import six


class ApiCallHandler(Handler):
    """Api call handler class."""

    def __init__(self, api, call, *args, **kwargs):
        super(ApiCallHandler, self).__init__(api)
        self._call = call
        self._args = args
        self._kwargs = kwargs
        self._result = None
        self._ready = False
        self._timeout = 0.1

    @property
    def result(self):
        return self._result

    @property
    def ready(self):
        return self._ready

    def handle_connect(self):
        self._result = getattr(self.api, self._call)(*self._args,
                                                     **self._kwargs)
        self._ready = True
        while self.api.transport.connected:
            time.sleep(self._timeout)


class DeviceHiveApi(object):
    """Device hive api class."""

    def __init__(self, transport_url, **options):
        self._transport_url = transport_url
        self._transport_alive_timeout = options.pop('transport_alive_timeout',
                                                    0.01)
        options['transport_keep_alive'] = False
        options['api_init'] = False
        self._options = options

    @staticmethod
    def _error_method(*args, **kwargs):
        raise AttributeError('Method is not allowed in this context.')

    @staticmethod
    def _unset_methods(entity, methods):
        [setattr(entity, method, DeviceHiveApi._error_method)
         for method in methods]

    @staticmethod
    def _unset_device_methods(device):
        unset_methods = ['subscribe_insert_commands',
                         'unsubscribe_insert_commands',
                         'subscribe_update_commands',
                         'unsubscribe_update_commands',
                         'subscribe_notifications',
                         'unsubscribe_notifications']
        DeviceHiveApi._unset_methods(device, unset_methods)

    @staticmethod
    def _unset_network_methods(network):
        unset_methods = ['list_devices']
        DeviceHiveApi._unset_methods(network, unset_methods)

    def _call(self, call, *args, **kwargs):
        device_hive = DeviceHive(ApiCallHandler, call, *args, **kwargs)
        device_hive.connect(self._transport_url, **self._options)
        while not device_hive.handler.ready:
            time.sleep(self._transport_alive_timeout)
            if device_hive.transport.exception_info:
                six.reraise(*device_hive.transport.exception_info)
        return device_hive.handler.result

    def get_info(self):
        return self._call('get_info')

    def get_cluster_info(self):
        return self._call('get_cluster_info')

    def get_property(self, name):
        return self._call('get_property', name)

    def set_property(self, name, value):
        return self._call('set_property', name, value)

    def delete_property(self, name):
        return self._call('delete_property', name)

    def create_token(self, *args, **kwargs):
        return self._call('create_token', *args, **kwargs)

    def refresh_token(self):
        return self._call('refresh_token')

    def list_devices(self, *args, **kwargs):
        devices = self._call('list_devices', *args, **kwargs)
        [self._unset_device_methods(device) for device in devices]
        return devices

    def get_device(self, *args, **kwargs):
        device = self._call('get_device', *args, **kwargs)
        self._unset_device_methods(device)
        return device

    def put_device(self, *args, **kwargs):
        device = self._call('put_device', *args, **kwargs)
        self._unset_device_methods(device)
        return device

    def list_networks(self, *args, **kwargs):
        networks = self._call('list_networks', *args, **kwargs)
        [self._unset_network_methods(network) for network in networks]
        return networks

    def get_network(self, *args, **kwargs):
        network = self._call('get_network', *args, **kwargs)
        self._unset_network_methods(network)
        return network

    def create_network(self, *args, **kwargs):
        network = self._call('create_network', *args, **kwargs)
        self._unset_network_methods(network)
        return network

    def list_users(self, *args, **kwargs):
        return self._call('list_users', *args, **kwargs)

    def get_current_user(self):
        return self._call('get_current_user')

    def get_user(self, *args, **kwargs):
        return self._call('get_user', *args, **kwargs)

    def create_user(self, *args, **kwargs):
        return self._call('create_user', *args, **kwargs)

    def disconnect(self):
        self._call('disconnect')
