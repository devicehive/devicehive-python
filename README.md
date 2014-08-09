devicehive ![build status](https://travis-ci.org/devicehive/devicehive-python.svg?branch=stable)
==========
*a Twisted implementation of Device-Hive client protocol v8*

What's new in 0.0.2
===================

* `devicehive.DeviceDelegate` class was replaced with `devicehive.interfaces.IProtoHandler` interface.
* long polling transport related classes were moved into separate module (`devicehive.poll`).
* web-socket transport support has been added (`devicehive.ws` module).
* `devicehive.auto.AutoFactory` was added - factory which select devicehive transport depends on info-call result.
* under `devicehive.gateway` a few classes have been added which support creation of a custom gateway.
* gateway's binary protocol has been added
* an IProtoHandler instance can implement logic for a few devices at once.


Prerequisites
-------------

Before reading this tutorial you should know a bit of Python. If you wish to work example
in this tutorial you also have to install some software on your computer or target
device:

* Python 2.7 http://python.org
* Twisted http://twistedmatrix.com
* devicehive python library http://devicehive.com


Installation
------------

Certainly, you may skip this section and bundle entire devicehive library with
your application. In some situations it may be a case. But more common way to
work with devicehive library is to install it first. The simplest way to do this
is to run command:

```
	python setup.py install
```

In case if setuptools is installed on your computer the command above
will automatically install devicehive library itself and all necessary
dependencies (actually there is only one dependency - twisted). Otherwise you
should to download and install dependencies manually or use one of methods
described in Python Package Index tutorial http://wiki.python.org/moin/CheeseShopTutorial.



Creating a simple client
------------------------
Creating a simple application using new version of  library is not much harder then is was before.
The only difference is that now you need to implement `devicehive.interfaces.IProtoHandler` interface
instead of overriding `devicehive.DeviceDelegate` class methods.

This way now your application class has to implement all methods which `IProtoHandler` interface defines.
This means that you class most likly will look like this:

```python
    class YourApplicationClass(object):
        zope.interface.implements(devicehive.interfaces.IProtoHandler)
        def on_apimeta(self, websocket_server, server_time):
            pass
        def on_connected(self):
            pass
        def on_connection_failed(self, reason) :
            pass
        def on_closing_connection(self): 
            pass
        def on_failure(self, device_id, reason):
            pass
        def on_command(self, device_id, command, finished):
            pass
```

For instance, if your application does not requires to handle transport failures then you
may leave `on_failure` method empty.

Here I need to mention that during protocol-factory initialization it will set a reference to itself in
`YourApplication.factory` attribute. And every devicehive protocol-factory implements
`devicehive.interfaces.IProtoFactory` interface. And using factory methods an application of yours can
interact upon underlying devicehive protocol. For example, it can send a notification
message using `self.factory.notify(...)` call. Or it can register one or more devices
using `self.factory.device_save` method. For a simple application the most appropriate place to register
device would be on_connected method.

```python
    def on_connected(self):
        self.factory.device_save(iDeviceInfoInstance)
```

A class which you pass into device_save method has to conform to `devicehive.interfaces.IDeviceInfo` interface.
We suggested that implementation of `IDeviceInfo` interface will not differ to much from application to application,
that is why we included it's typical implementation into `devicehive.DeviceInfo` class. Also under `devicehive.*` namespace
you will find a few other classes which will be helpfull during constuction of `IDeviceInfo` object. These are:
* `devicehive.Network` is a typical implementation of `devicehive.interfaces.INetwork` interface.
* `devicehive.DeviceClass` - implements `devicehive.interfaces.IDeviceClass`.
* and `devicehive.Equipment` which implements `devicehive.interfaces.IEquipment` interface.
Please see complete description of `IProtoFactory` methods in `devicehive.interfaces` module's documentation.

I would also like to note that protocol factories do not do any additional verifications and will allow you, lets say,
to call `notify()` method even before devicehive connection had been established. Application of yours has to implement
all neccessary logic to avoid such situations.


In order to handle device-hive command your application has to allow it for specific device by
calling factory.subscribe method. Command handling should be done in on_command method. The procedure of command
handling in the new version of the library did not changed much. Except that in the new version `on_command` method
expects `device_info` variable and `command` parameter now implements `devicehive.interfaces.ICommand` interface.
The `device_info` variable specifies for which device a command was sent.


Using device-hive gateway API
-----------------------------

Device-Hive gateway is built on the same principles as the client API. `devicehive.gateway.IGateway` defines the
interface to which every custom gateway has to be conformed to. Although in most cases it would be appropriate to
use `devicehive.BaseGateway` class as a starting point of your custom implementation.
In file `basic_gateway_example.py` you can see such an implementation. This example creates Gateway class instance.
A constructor of this class expects devicehive URL as it's first parameter and a class of protocol-factory as it's
second parameter. This protocol-factory will be used to form transport layer between gateway and device-hive server.
A end point and it's protocol factory define a channel and a protocol which will be used to transfer commands
between gateway and end device.
Thus to customize Gateway's behaviuor you need to override BaseGateway's class methods. An if you want to change
device-to-gateway transport you will need to provide a protocol-factory implementation of that transport into
gateway 'run' method.


Conclusion
----------

In this tutorial we have implemented the simplest Device-Hive application. For more examples please
see examples subdirectory under devicehive python library distribution. And of cause you may use python
build-in help system to take a closer look at library's API.
For further reading please see examples under examples folder.

