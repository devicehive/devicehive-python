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
