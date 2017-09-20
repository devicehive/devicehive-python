![build status](https://travis-ci.org/devicehive/devicehive-python.svg?branch=stable)

# Devicehive

## Creating a client

Creating a client with a new version of library is very simple.
First of all you need to create custom `Handler` class.

Example of creating custom `Handler` class:

```python
from devicehive import Handler


class SimpleHandler(Handler):

    def handle_connect(self):
        info = self.api.get_info()
        print(info)
        self.api.disconnect()
```

`handle_connect` is the only one required method. If you want to handle server 
events you heed to implement `handle_command_insert`, `handle_command_update` 
and `handle_notification` methods. Here is the example:

```python
from devicehive import Handler


class SimpleHandler(Handler):
    
    def handle_connect(self):
        device_ids = ['example-device-1', 'example-device-2']
        for device_id in device_ids:
            self.api.put_device(device_id)
        self.api.subscribe_insert_commands(device_ids)
        self.api.subscribe_update_commands(device_ids)
        self.api.subscribe_notifications(device_ids)

    def handle_command_insert(self, command):
        print(command.command)

    def handle_command_update(self, command):
        print(command.command)

    def handle_notification(self, notification):
        print(notification.notification)
```

The second step is to use `DeviceHive` class for creating connection to the 
server.

Example:

```python
from devicehive import Handler
from devicehive import DeviceHive


class SimpleHandler(Handler):

    def handle_connect(self):
        device_ids = ['example-device-1', 'example-device-2']
        for device_id in device_ids:
            self.api.put_device(device_id)
        self.api.subscribe_insert_commands()
        self.api.subscribe_update_commands()
        self.api.subscribe_notifications()

    def handle_command_insert(self, command):
        print(command.command)

    def handle_command_update(self, command):
        print(command.command)

    def handle_notification(self, notification):
        print(notification.notification)


url = 'http://playground.dev.devicehive.com/api/rest'
refresh_token = 'SOME_REFRESH_TOKEN'
dh = DeviceHive(SimpleHandler)
dh.connect(url, refresh_token=refresh_token)
```

### Custom handler args

If you need to initialize your handler you can do it the next way:

```python
from devicehive import Handler
from devicehive import DeviceHive


class SimpleHandler(Handler):

    def __init__(self, api, some_arg, some_kwarg):
        Handler.__init__(self, api)
        self._some_arg = some_arg
        self._some_kwarg = some_kwarg

    def handle_connect(self):
        info = self.api.get_info()
        print(info)
        self.api.disconnect()

dh = DeviceHive(SimpleHandler, 'some_arg', some_kwarg='some_kwarg')
```

### Websocket protocol

If you want to use `Websocket` protocol you need only to specify the url:

```python
url = 'ws://playground.dev.devicehive.com/api/websocket'
```

### Authentication

There are three ways of initial authentication:

* Using refresh token
* Using access token
* Using login and password

Examples:

```python
url = 'ws://playground.dev.devicehive.com/api/websocket'
dh.connect(url, refresh_token='SOME_REFRESH_TOKEN')
```

```python
url = 'ws://playground.dev.devicehive.com/api/websocket'
dh.connect(url, access_token='SOME_ACCESS_TOKEN')
```

```python
url = 'ws://playground.dev.devicehive.com/api/websocket'
dh.connect(url, login='SOME_LOGIN', password='SOME_PASSWORD')
```

## API

All api calls may be done via `api` object. This object available inside
custom handler with `self.api`.

### Info

`self.api.get_info()` returns `dict` with the next fields:

* `api_version`
* `server_timestamp`
* `rest_server_url`
* `websocket_server_url`

`self.api.get_cluster_info()` returns `dict` with the next fields:

* `bootstrap.servers`
* `zookeeper.connect`

Example:
```python
from devicehive import Handler


class SimpleHandler(Handler):

    def handle_connect(self):
        info = self.api.get_info()
        print(info)
        cluster_info = self.api.get_cluster_info()
        print(cluster_info)
        self.api.disconnect()
```

### Properties

`self.api.get_property(name)` returns `dict` with the next fields:

* `entity_version`
* `name`
* `value`

`self.api.set_property(name, value)` returns entity version.

`self.api.delete_property(name)` does not return anything.

Example:
```python
from devicehive import Handler


class SimpleHandler(Handler):

    def handle_connect(self):
        name = 'user.login.lastTimeoutSent'
        prop = self.api.get_property(name)
        print(prop)
        entity_version = self.api.get_property(name, 'value')
        print(entity_version)
        self.api.delete_property(name)
        self.api.disconnect()
```

### Tokens

`self.api.create_token(user_id, expiration, actions, network_ids, device_ids)`
returns `dict` with the next fields:

* `access_token`
* `refresh_token`

only `user_id` arg is required.

`self.api.refresh_token()` refreshes the access token and returns it.

Example:
```python
from devicehive import Handler


class SimpleHandler(Handler):

    def handle_connect(self):
        tokens = self.api.create_token(1)
        print(tokens)
        access_token = self.api.refresh_token()
        print(access_token)
        self.api.disconnect()
```

### Commands subscription and unsubscription

`self.api.subscribe_insert_commands(device_ids, names, timestamp)`
does not return anything.

`self.api.subscribe_update_commands(device_ids, names, timestamp)`
does not return anything.

Only `device_ids` arg is required.

`self.api.unsubscribe_insert_commands(device_ids)` does not return anything.
`self.api.unsubscribe_update_commands(device_ids)` does not return anything.

Example:
```python
from devicehive import Handler


class SimpleHandler(Handler):

    def handle_connect(self):
        device_id = 'example-device'
        device = self.api.put_device(device_id)
        command_name = 'example-command'
        self.api.subscribe_insert_commands([device_id], [command_name])
        self.api.subscribe_update_commands([device_id], [command_name])
        command = device.send_command(command_name)
        command.status = 'new-status'
        command.save()

    def handle_command_insert(self, command):
        print('Command insert: %s, status: %s.' % (command.command,
                                                   command.status))

    def handle_command_update(self, command):
        print('Command update: %s, status: %s.' % (command.command,
                                                   command.status))
        self.api.unsubscribe_insert_commands(['example-device'])
        self.api.unsubscribe_update_commands(['example-device'])
```

### Notifications subscription and unsubscription

`self.api.subscribe_notifications(device_ids, names, timestamp)` does not return
anything. Only `device_ids` arg is required.

`self.api.unsubscribe_notifications(device_ids)` does not return anything.

Example:
```python
from devicehive import Handler


class SimpleHandler(Handler):

    def handle_connect(self):
        device_id = 'example-device'
        device = self.api.put_device(device_id)
        notification_name = 'example-notification'
        self.api.subscribe_notifications([device_id], [notification_name])
        device.send_notification(notification_name)

    def handle_notification(self, notification):
        print('Notification: %s.' % notification.notification)
        self.api.unsubscribe_notifications(['example-device'])
```

### Devices

`self.api.list_devices(name, name_pattern, network_id, network_name, sort_field,
                       sort_order, take, skip)` returns list of `Device`
objects. All args are optional.

`self.api.get_device(device_id)` returns `Device` object.

`self.api.put_device(device_id, name, data, network_id, is_blocked)`

Only `device_id` arg is required.

#### Device object

Properties:

* `id` (read only)
* `name`
* `data`
* `network_id`
* `is_blocked`

Methods:

* `save()` Does not return anything.
* `remove()` Does not return anything.
* `subscribe_insert_commands(names, timestamp)` Does not return anything. All args are optional.
* `unsubscribe_insert_commands()` Does not return anything.
* `subscribe_update_commands(names, timestamp)` Does not return anything. All args are optional.
* `unsubscribe_update_commands()` Does not return anything.
* `list_commands(start, end, command, status, sort_field, sort_order, take, skip)` Returns list of `Command` objects. All args are optional.
* `send_command(command_name, parameters, lifetime, timestamp, status, result)` Returns `Command` object. Only `command_name` is required.
* `subscribe_notifications(names, timestamp)` Does not return anything. All args are optional.
* `unsubscribe_notifications()` Does not return anything.
* `list_notifications(start, end, notification, sort_field, sort_order, take, skip)` Returns list of `Notification` objects. All args are optional.
* `send_notification(notification_name, parameters, timestamp)` Returns `Notification` object. Only `notification_name` is required.

#### Command object

Properties:

* `id` (read only)
* `user_id` (read only)
* `command` (read only)
* `parameters` (read only)
* `lifetime` (read only)
* `timestamp` (read only)
* `last_updated` (read only)
* `status`
* `result`

Methods:

* `save()` Does not return anything.

#### Notification object

Properties:

* `device_id` (read only)
* `id` (read only)
* `notification` (read only)
* `parameters` (read only)
* `timestamp` (read only)

Example:
```python
from devicehive import Handler


class SimpleHandler(Handler):

    def handle_connect(self):
        device_id = 'example-device'
        device = self.api.put_device(device_id)
        device.name = 'new-device-name'
        device.data = {'key': 'value'}
        device.save()
        devices = self.api.list_devices()
        for device in devices:
            print('Device: %s, name: %s, data: %s' % (device.id, device.name,
                                                      device.data))
            device.remove()
        self.api.disconnect()
```

### Networks

`self.api.list_networks(name, name_pattern, sort_field, sort_order, take, skip)`
returns list of `Network` objects. All args are optional.

`self.api.get_network(network_id)` returns `Network` object.

`self.api.create_network(name, description)` returns `Network` object.

#### Network object

Properties:

* `id` (read only)
* `name`
* `description`

Methods:

* `save()` Does not return anything.
* `remove()` Does not return anything.
* `list_devices(name, name_pattern, sort_field, sort_order, take, skip)` Returns list of `Device` objects. All args are optional.

Example:
```python
from devicehive import Handler


class SimpleHandler(Handler):

    def handle_connect(self):
        network_name = 'example-name'
        network_description = 'example-description'
        network = self.api.create_network(network_name, network_description)
        print(network.name)
        self.api.disconnect()
```

### Users

`self.api.list_users(login, login_pattern, role, status, sort_field, sort_order,
                     take, skip)` returns list of `User` objects. All args are
                     optional.

`self.api.get_current_user()` returns `User` object.

`self.api.get_user(user_id)` returns `User` object.

`self.api.create_user(self, login, password, role, data)` returns `User` object.

#### User object

Properties:

* `id` (read only)
* `login` (read only)
* `last_login` (read only)
* `intro_reviewed` (read only)
* `role`
* `status`
* `data`

Methods:

* `save()` Does not return anything.
* `update_password(password)` Does not return anything.
* `remove()` Does not return anything.
* `list_networks()` Returns list of `Network` objects.
* `assign_network(network_id)` Does not return anything.
* `unassign_network(network_id)` Does not return anything.

Example:
```python
from devicehive import Handler
from devicehive.user import User


class SimpleHandler(Handler):

    def handle_connect(self):
        login = 'example-login'
        password = 'example-password'
        role = User.CLIENT_ROLE
        data = {'key': 'value'}
        user = self.api.create_user(login, password, role, data)
        print(user.login)
        self.api.disconnect()
```

## Extended example

Here we will create one endpoint which sends notifications and other endpoint 
which receives these notifications.

On the first we will create `receiver.py`:

```python
from devicehive import Handler
from devicehive import DeviceHive


class ReceiverHandler(Handler):

    def __init__(self, api, device_id='simple-example-device',
                 accept_command_name='accept_notifications'):
        Handler.__init__(self, api)
        self._device_id = device_id
        self._accept_command_name = accept_command_name
        self._device = None

    def handle_connect(self):
        self._device = self.api.put_device(self._device_id)
        self._device.subscribe_insert_commands([self._accept_command_name])
        self._device.subscribe_notifications()

    def handle_command_insert(self, command):
        print('Accept command "%s"' % self._accept_command_name)
        command.status = 'accepted'
        command.save()

    def handle_notification(self, notification):
        print('Notification "%s" received' % notification.notification)


url = 'ws://playground.dev.devicehive.com/api/websocket'
refresh_token = 'SOME_REFRESH_TOKEN'
dh = DeviceHive(ReceiverHandler)
dh.connect(url, refresh_token=refresh_token)
```

On the next step we will create `sender.py`

```python
from devicehive import Handler
from devicehive import DeviceHive


class SenderHandler(Handler):

    def __init__(self, api, device_id='simple-example-device',
                 accept_command_name='accept_notifications',
                 num_notifications=10):
        Handler.__init__(self, api)
        self._device_id = device_id
        self._accept_command_name = accept_command_name
        self._num_notifications = num_notifications
        self._device = None

    def _send_notifications(self):
        for num_notification in range(self._num_notifications):
            notification = '%s-notification' % num_notification
            self._device.send_notification(notification)
            print('Sending notification "%s"' % notification)
        self.api.disconnect()

    def handle_connect(self):
        self._device = self.api.get_device(self._device_id)
        self._device.send_command(self._accept_command_name)
        print('Sending command "%s"' % self._accept_command_name)
        self._device.subscribe_update_commands([self._accept_command_name])

    def handle_command_update(self, command):
        if command.status == 'accepted':
            print('Command "%s" accepted' % self._accept_command_name)
            self._send_notifications()


url = 'http://playground.dev.devicehive.com/api/rest'
refresh_token = 'SOME_REFRESH_TOKEN'
dh = DeviceHive(SenderHandler)
dh.connect(url, refresh_token=refresh_token)
```

Run `python receiver.py` in the first terminal. And `python sender.py` in the
second. The order of run is important. `receiver.py` must be started first.
