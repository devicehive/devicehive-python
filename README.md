![build status](https://travis-ci.org/devicehive/devicehive-python.svg?branch=stable)

# Devicehive

## Creating a simple client

Creating a simple client with a new version of library is very simple.
First of all you need to create `Handler` class.

Example of creating simple `Handler` class:

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
