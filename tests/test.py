import threading
import six
from six.moves import range as six_range
from collections import defaultdict
from devicehive import Handler
from devicehive import DeviceHiveApi
from devicehive import DeviceHive
import time
import pytest


if six.PY2:
    class TimeoutError(OSError):
        pass


class TestHandler(Handler):
    """Test handler class."""

    def __init__(self, api, handle_connect, handle_command_insert,
                 handle_command_update, handle_notification):
        super(TestHandler, self).__init__(api)
        self._handle_connect = handle_connect
        self._handle_command_insert = handle_command_insert
        self._handle_command_update = handle_command_update
        self._handle_notification = handle_notification
        self.data = {}

    def handle_connect(self):
        self._handle_connect(self)
        if not any([self._handle_command_insert, self._handle_command_update,
                    self._handle_notification]):
            self.disconnect()

    def handle_command_insert(self, command):
        if not self._handle_command_insert:
            return
        self._handle_command_insert(self, command)

    def handle_command_update(self, command):
        if not self._handle_command_update:
            return
        self._handle_command_update(self, command)

    def handle_notification(self, notification):
        if not self._handle_notification:
            return
        self._handle_notification(self, notification)

    def disconnect(self):
        self.api.disconnect()


class Test(object):
    """Test class."""
    _entity_ids = None

    # entity types
    USER_ENTITY = 'user'
    DEVICE_ENTITY = 'device'
    NETWORK_ENTITY = 'network'

    def __init__(self, transport_url, refresh_token, token_type):
        self._transport_url = transport_url
        self._refresh_token = refresh_token
        self._token_type = token_type
        self._transport_name = DeviceHive.transport_name(self._transport_url)
        self._entity_ids = defaultdict(list)
        self._is_handle_timeout = False

    def _generate_id(self, key=None):
        time_key = repr(time.time()).replace('.', '')
        if not key:
            return '%s-%s-%s' % (self._transport_name, self._token_type,
                                 time_key)
        return '%s-%s-%s-%s' % (self._transport_name, key, self._token_type,
                                time_key)

    def generate_id(self, key=None, entity_type=None):
        entity_id = self._generate_id(key=key)
        self._entity_ids[entity_type].append(entity_id)
        return entity_id

    def generate_ids(self, key=None, entity_type=None, count=1):
        base_entity_id = self._generate_id(key=key)
        entity_ids = ['%s-%s' % (base_entity_id, i) for i in six_range(count)]
        self._entity_ids[entity_type].extend(entity_ids)
        return base_entity_id, entity_ids

    @property
    def entity_ids(self):
        return self._entity_ids

    @property
    def transport_name(self):
        return self._transport_name

    @property
    def http_transport(self):
        return self._transport_name == 'http'

    @property
    def websocket_transport(self):
        return self._transport_name == 'websocket'

    @property
    def user_refresh_token(self):
        return self._token_type == 'user'

    @property
    def admin_refresh_token(self):
        return self._token_type == 'admin'

    def only_user_implementation(self):
        if self.user_refresh_token:
            return
        pytest.skip('Implemented only for user refresh token.')

    def only_admin_implementation(self):
        if self.admin_refresh_token:
            return
        pytest.skip('Implemented only for admin refresh token.')

    def only_http_implementation(self):
        if self.http_transport:
            return
        pytest.skip('Implemented only for http transport.')

    def only_websocket_implementation(self):
        if self.websocket_transport:
            return
        pytest.skip('Implemented only for websocket transport.')

    def device_hive_api(self):
        return DeviceHiveApi(self._transport_url,
                             refresh_token=self._refresh_token)

    def _on_handle_timeout(self, device_hive):
        device_hive.handler.api.disconnect()
        self._is_handle_timeout = True

    def run(self, handle_connect, handle_command_insert=None,
            handle_command_update=None, handle_notification=None,
            handle_timeout=60):
        handler_kwargs = {'handle_connect': handle_connect,
                          'handle_command_insert': handle_command_insert,
                          'handle_command_update': handle_command_update,
                          'handle_notification': handle_notification}
        device_hive = DeviceHive(TestHandler, **handler_kwargs)
        timeout_timer = threading.Timer(handle_timeout, self._on_handle_timeout,
                                        args=(device_hive,))
        timeout_timer.setDaemon(True)
        timeout_timer.start()
        device_hive.connect(self._transport_url,
                            refresh_token=self._refresh_token)
        timeout_timer.cancel()

        if self._is_handle_timeout:
            raise TimeoutError('Waited too long for handle.')
