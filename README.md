devicehive - is a Twisted implementation of Device-Hive client protocol v6.


devicehive 0.0.1 tutorial
=========================

Prerequisites
-------------

Before reading this tutorial you should know a bit of Python. If you wish to work example
in this tutorial you also have to install some software on your computer or target
device:

	- Python 2.7 http://python.org
	- Twisted http://twistedmatrix.com
	- devicehive python library http://devicehive.com


Installation
------------

Certainly, you may skip this section and bundle entire devicehive library with
your application. In some situations it may be a case. But more common way to
work with devicehive library is to install it first. The simplest way to do this
is to run command:

	python setup.py install

	In case if setuptools is installed on your computer the command above
will automatically install devicehive library itself and all necessary
dependencies (actually there is only one dependency - twisted). Otherwise you
should to download and install dependencies manually or use one of methods
described in Python Package Index tutorial http://wiki.python.org/moin/CheeseShopTutorial.


Creating a simple client
------------------------

	The very fist thing you need to do to start working with devicehive library
is to write the following code:

	from devicehive import HTTP11DeviceHiveFactory, DeviceDelegate, Equipment, CommandResult
	from twisted.internet import reactor

	The import statement above enumerates all classes which devicehive library
provides for your use. HTTP11DeviceHiveFactory is a client factory in terms of Twisted. You
may use its parameters to tune factory and protocol behaviour. Equipment and CommandResult classes
are utility classes and in general they were added into library just to increase readability. Therefore
the main class your will work with is a DeviceDelegate.
	DeviceDelegate is an abstract class. Devicehive library uses it's methods to obtain description of
your device. This means that your need to override these mandatory abstract
methods like in the following code:

	class MyDeviceDelegate(devicehive.DeviceDelegate):
		def device_id(self):
			return 'E50D6085-2ABA-48E9-B1C3-73C673E414BE'
		def device_key(self):
			return 'device-key'
		def device_name(self):
			return 'DeviceHive Python Example'
		def device_status(self):
			return 'Online'
		def network_name(self):
			return 'Netname'
		def network_description(self):
			return 'Description'
		def device_class_name(self):
			return 'RGB Led Network'
		def device_class_version(self):
			return '1.0'
		def device_class_is_permanent(self):
			return False
		def equipment(self):
			return [devicehive.Equipment(name = 'LED', code = 'LED_CODE', _type = 'LED_TYPE'), ]

Please see protocol description to understand the purpose of overridden methods.
The next thing we need to acomplish is to actually run protocol implementation.

	if __name__ == '__main__' :
		my_device_delegate = MyDeviceDelegate()
		factory = devicehive.HTTP11DeviceHiveFactory(device_delegate = my_device_delegate)
		reactor.connectDeviceHive("http://ecloud.dataart.com/ecapi6/", factory)
		reactor.run()


Code above creates an instance of MyDeviceDelegate class which was created on the previous step,
creates protocol factory and passes deviec-delegate variable as a parameter into it. Then code
calls reactor.connectDeviceHive method which accept URL to Device-Hive server as a first parameter
and protocol factory as a second prameter. And finally it runs twisted reactor.


Handling commands and Sending notifications
-------------------------------------------

In the previous steps, we created complete device-hive application. Despite that there is only a
few lines of code were written it actually does a lot. It registers the device in device-hive server,
acquire commands, sends reports and notifications if necessary. Unfortunately right now we do not
have any influence on this process. To change the things and do handling of upcoming command it
is needed to override method

	def do_command(self, command, finish_deferred):
		pass

in DeviceDelegate class. Every time a command is sent to you device the DeviceDelegate.do_command
method will be called. The first parameter is a json commad object decoded into python's dict type.
The typical structure of of this command-object will look like:

	{'command' = 'command_name', 'parameters': [ LIST_OF_COMMAND_PARAMETERS ]}

	Because command processing may take a while and thus it may block the rest of the
library, it is good idea to make it asynchronous. In order to support such an approach
devicehive library passes Deferred object as a second parameter into the do_command method.
callback method of finish_deferred expects devicehive.CommandResult object as a parameter.

	def do_command(self, command, finish_deferred):
		# do something
		finish_deferred.callback(CommandResult("status", "result of operation"))

Invokation of deferred`s callback method will result in Report-request to Device-Hive server.
When you do not need to report Result parameter you may use the following code:

	def do_command(self, command, finish_deferred):
		# do something
		finish_deferred.callback("Completed")

In case of error you still may use callback method with specially encoded values passed
in a Status and a Result parameters into CommandResult contructor. But more convenient method
to report callee about exceptions thrown is to use errback method of the finish_deferred object.

	...
 	finish_deferred.errback(Exception("Exception description."))
 	...

And finally at any time you may notify listeners about events happened in your device by 
	
	...
	device_delegate_instance.notify('notification', parameter1='value', prameter_to_send2='value2')
	...

You may send as many parameters as you want until their names and values are conform
client side API.


Conclusion
----------

	In this tutorial we have implemented the simplest Device-Hive application. For more examples please
see examples subdirectory under devicehive python library distribution. And of cause you may use python
build-in help system to take a closer look at library's API.

