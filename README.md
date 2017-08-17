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
```

`handle_connect` is the only one required method. If you want to handle server 
events you heed to implement `handle_command_insert`, `handle_command_update` 
and `handle_notification` methods. Here is the example:

```python
from devicehive import Handler


class SimpleHandler(Handler):
    
    def handle_connect(self):
        self.api.subscribe_insert_commands()
        self.api.subscribe_update_commands()
        self.api.subscribe_notifications()

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
dh.join()
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

dh = DeviceHive(SimpleHandler, 'some_arg', some_kwarg='some_kwarg')
```

### Websocket protocol

If you want to use `Websocket` protocol you need only to specify the url:

```python
url = 'ws://playground.dev.devicehive.com/api/websocket'
```

### Authentication.

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
anything.

Only `device_ids` arg is required.

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
objects. 

All args are optional.

`self.api.get_device(device_id)` returns `Device` object.

`self.api.put_device(device_id, name, data, network_id, is_blocked)`

Only `device_id` arg is required.

`Device` object:

Properties:
* `id` (read only)
* `name`
* `data`
* `network_id`
* `is_blocked`

Methods:
* `save()` Does not return anything.
* `remove()` Does not return anything.
* `subscribe_insert_commands(names, timestamp)` All args are optional.
* `unsubscribe_insert_commands()`
* `subscribe_update_commands(names, timestamp)` All args are optional.
* `unsubscribe_update_commands()`
* `list_commands(start, end, command, status, sort_field, sort_order, take,
                 skip)` All args are optional.
* `send_command(command_name, parameters, lifetime, timestamp, status, result)`
Only `command_name` is required.
* `subscribe_notifications(names, timestamp)` All args are optional.
* `unsubscribe_notifications()`
* `list_notifications(start, end, notification, sort_field, sort_order, take,
                      skip)` All args are optional.
* `send_notification(notification_name, parameters, timestamp)`
Only `notification_name` is required.
