# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

try:
    from smbus import SMBus
except ImportError:
    class SMBus(object):
        """
        Mock I2C interface.
        """
        def __init__(self, adaptor):
            print('SMBus adaptor 0 has been selected')
            self.adaptor = adaptor
            self.data = {}

        def write_i2c_block_data(self, dest_address, dest_register, data):
            if dest_address not in self.data:
                self.data[dest_address] = {dest_register: data}
            else:
                if dest_register not in self.data[dest_address]:
                    self.data[dest_address][dest_register] = data
                else:
                    self.data[dest_address][dest_register] += data

        def read_i2c_block_data(self, dest_address, dest_register, len=32):
            if (dest_address in self.data) and (dest_register in self.data[dest_address]):
                result = self.data[dest_address][dest_register]
                self.data[dest_address][dest_register] = []
                return result
            else:
                return []

from devicehive import Notification
from array import array
from thread import allocate_lock
from zope.interface import implements
from twisted.internet import reactor, threads, interfaces
from twisted.internet.protocol import ServerFactory, Protocol
from twisted.python import log


def LOG_INFO(msg):
    """
    Abstraction method for logging general purpose information.
    @type msg: C{str}
    @param msg: a message to be logged
    """
    log.msg('[info]\t{0}'.format(msg))


def LOG_ERR(msg):
    """
    Abstraction method for logging errors.
    @type msg: C{str}
    @param msg: a error message to be logged.
    """
    log.err('[error]\t{0}'.format(msg))


class I2cProtocol(Protocol):
    """
    Binary protocol implementation.
    """

    def __init__(self, factory):
        self.factory = factory
        self._lock = allocate_lock()

    def dataReceived(self, data):
        i2c_address, value = data
        self.factory.send_data_notification(i2c_address, value)

    def write_i2c(self, i2c_address, reg, data):
        with self._lock:
            self.transport.set_destination_address(i2c_address)
            self.transport.set_destination_register(reg)
            self.transport.set_destination_direction(0)
            return self.transport.write(data)

    def read_i2c(self, i2c_address, reg, data):
        with self._lock:
            self.transport.set_destination_address(i2c_address)
            self.transport.set_destination_register(reg)
            self.transport.set_destination_direction(1)
            return self.transport.write(data)

    def connectionLost(self, reason):
        return Protocol.connectionLost(self, reason)

    def makeConnection(self, transport):
        return Protocol.makeConnection(self, transport)

    def connectionMade(self):
        reactor.callLater(0, self.factory.on_connection_made)


class I2cProtoFactory(ServerFactory):
    addresses = []

    def __init__(self, gateway):
        self.protocol = None
        self.gateway = gateway
        self.pending_results = {}

    def on_connection_made(self):
        """
        This is a callback which indicates that protocol has established connection.
        """
        for i2c_address, info in self.addresses:
            self.gateway.registration_received(info)

    def send_data_notification(self, address, data):
        for device_info in [info for i2c_address, info in self.addresses if address == i2c_address]:
            self.gateway.notification_received(device_info, Notification('read-response', data))

    def do_command(self, device, command, finish_deferred):
        """
        This handler is called when a new command comes from DeviceHive server.
        @param device, C{object} which implements C{IDeviceInfo} interface
        @param command: C{object} which implements C{ICommand} interface
        """
        log.msg('A new command has came from a device-hive server to device "{0}".'.format(device))
        for i2c_address, device_info in [(i2c_address, info) for i2c_address, info in self.addresses if info.id == device.id]:
            if (command.command == 'write') and ('reg' in command.parameters) and ('data' in command.parameters):
                def on_ok(result):
                    finish_deferred.callback(result)

                def on_err(err):
                    finish_deferred.errback(err)
                self.protocol.write_i2c(i2c_address, command.parameters['reg'], command.parameters['data']).addCallbacks(on_ok, on_err)
            elif (command.command == 'read') and ('reg' in command.parameters) and ('data' in command.parameters):
                def on_ok(result):
                    finish_deferred.callback(result)

                def on_err(err):
                    finish_deferred.errback(err)
                self.protocol.read_i2c(i2c_address, command.parameters['reg'], command.parameters['data']).addCallbacks(on_ok, on_err)
            else:
                finish_deferred.errback('Unsupported command {0} was received.'.format(command.command))
            break
        else:
            finish_deferred.errback('Failed to find device_id {0} in the track list.'.format(device))

    def buildProtocol(self, addresses):
        self.addresses = addresses
        self.protocol = I2cProtocol(self)
        return self.protocol


class I2cTransport(object):
    """
    @ivar adaptor: i2c adaptor number to use
    @ivar poll_timeout: adaptor polling interval
    """

    implements(interfaces.ITransport)

    adaptor = 0
    poll_timeout = 10
    protocol = None

    dest_address = 0
    dest_register = 0
    dest_direction = 0

    def __init__(self, _reactor, protocol, adaptor, addresses):
        """
        @param _reactor: reference to twisted reactor
        @param protocol: a C{twisted.internet.interfaces.IProtocol} protocol which handles i2c channel
        @param adaptor: C{int} adaptor number
        @param addresses: C{tuple} of i2c slaves addresses
        """
        self.adaptor = adaptor
        self.bus = SMBus(self.adaptor)
        self.addresses = addresses
        self.adaptor_lock = allocate_lock()

        def shutdown_handler():
            LOG_INFO('A request to shutdown twisted reactor has been received. Closing I2C adaptor {0}.'.format(self.adaptor))
            self.stop()

        _reactor.addSystemEventTrigger('before', 'shutdown', shutdown_handler)
        self.protocol = protocol
        self.protocol.makeConnection(self)

    def set_destination_address(self, address):
        self.dest_address = address

    def set_destination_device(self, index):
        """
        Method set destination address to be used with following write calls.
        @param index: an C{int} index of destination address
        """
        if not isinstance(index, int) and not isinstance(index, long):
            raise TypeError('int index expected')
        if index < 0 or index > len(self.addresses):
            raise ValueError('Addresses index is out of range.')
        address = self.addresses[index]
        if address != self.dest_address:
            self.dest_register = 0
            self.dest_direction = 0
        self.dest_address = address
        return self.dest_address

    def set_destination_register(self, register):
        """
        Sets destination register for the subsequent write operations.
        @param register:
        """
        if isinstance(register, unicode):
            register = int(register)
        elif not isinstance(register, int):
            raise TypeError('Type of register parameter should be unicode or int.')
        self.dest_register = register

    def set_destination_direction(self, direction):
        """
        Sets direction of the subsequent write operations.

        @param direction: 0 means write operation, 1 - read
        """
        if not isinstance(direction, int):
            raise TypeError('direction parameter should be of int type.')
        self.dest_direction = direction

    def start(self):
        """
        I2C gateway does not pull devices. In this implementation a read operation
        is triggered by client side only.
        """
        pass

    def stop(self):
        return True

    def write(self, data):
        """
        Method writes data into selected i2c slave.
        @param data: C{str} to be sent into i2c slave.
        @return: C{twisted.internet.defer.Deferred}
        """
        if self.dest_direction == 0:
            if (not isinstance(data, list)) or (len(data) > 32):
                raise TypeError('data must be a list of at least one, but not more than 32 integers')
        elif isinstance(data, unicode):
            data = int(data)
        elif not isinstance(data, int):
            raise TypeError('Type of data parameter should be unicode or int.')

        def write_thread(adaptor_lock, bus, dest_address, dest_direction, dest_register, data):
            """
            The thread dedicated to write data into i2c slave.
            @param adaptor_lock: C{threading.Lock}
            @param bus: a reference to C{smbus.SMBus} object.
            @param dest_address: C{int} which represents destination address
            @param dest_direction: C{int} determines direction of the subsequent operation
            @param dest_register: C{int} register to be read in the subsequent read operation
            @param data: a C{str} to be written into i2c slave.
            """
            LOG_INFO('Writing data into {0} i2c slave.'.format(dest_address))
            if dest_direction == 0:
                with adaptor_lock:
                    try:
                        bus.write_i2c_block_data(dest_address, dest_register, data)
                    except IOError, error:
                        LOG_ERR(str(error))
                        raise error
                LOG_INFO('The data has been successfully written into {0} i2c slave register {1}.'.format(dest_address, dest_register))
            else:
                LOG_INFO('dest address type {0}, register type {1} == {2}'.format(type(dest_address), type(dest_register), dest_register))
                with adaptor_lock:
                    try:
                        data_out = bus.read_i2c_block_data(dest_address, dest_register, data)
                    except IOError, error:
                        LOG_ERR(str(error))
                        raise error
                LOG_INFO('The data has been successfully read from {0} i2c slave register {1}.'.format(dest_address, dest_register))
                self.protocol.dataReceived((dest_address, data_out))
        return threads.deferToThread(write_thread, self.adaptor_lock, self.bus, self.dest_address, self.dest_direction, self.dest_register, data)

    def writeSequence(self, data_list):
        """
        Method writes list of string into i2c slave.
        @param data_list: a C{list} of strings to written into i2c slave register.
        """
        if not isinstance(data_list, list) and not isinstance(data_list, tuple):
            raise TypeError('data should be of list or tuple type.')
        if 0 < self.dest_address >= len(self.addresses):
            raise ValueError('Destination address index is out of range.')
        def write_thread(adaptor_lock, bus, dest_address, dest_direction, dest_register, data_list):
            """
            This thread writes strings into i2c slave.
            @param adaptor_lock: C{threading.Lock} object which arbiters access to I2C hardware.
            @param bus: a reference to C{smbus.SMBus} object.
            @param dest_address: a C{tuple} of addresses to poll.
            @param
            @param data_list: a C{list} of strings to send into i2c slave.
            """
            LOG_INFO('Writing list of string into i2c slave.'.format(dest_address))
            if dest_direction == 0:
                for item in data_list:
                    with adaptor_lock:
                        bus.write_i2c_block_data(dest_address, dest_register, list(array('B', item.encode('utf-8'))))
                        LOG_INFO('A data has been written into i2c slave {0}.'.format(dest_address))
            else:
                with adaptor_lock:
                    data_out = bus.read_i2c_block_data(dest_address, dest_register)
                LOG_INFO('The data has been successfully read from {0} i2c slave register {1}.'.format(dest_address, dest_register))
                self.protocol.dataReceived((dest_address, data_out))
        return threads.deferToThread(write_thread, self.bus, self.dest_address, self.dest_direction, self.dest_register, data_list)

    def lostConnection(self):
        pass

    def getPeer(self):
        raise NotImplementedError('getPeer method is not implemented for I2cTransport.')

    def getHost(self):
        raise NotImplementedError('getHost method is not implemented for I2cTransport.')


class I2cEndpoint(object):
    """
    I2C channel endpoint.

    Usage example:
        endpoint = SerialPortEndpoint(reactor, 'COM10', baud_rate=9600)
        endpoint.listen( BinaryProtocolFactory )
    """

    implements(interfaces.IStreamServerEndpoint)

    def __init__(self, reactor, adaptor, addresses):
        self.reactor = reactor
        self.adaptor = adaptor
        self.addresses = addresses

    def listen(self, proto_factory):
        proto = proto_factory.buildProtocol(self.addresses)
        return I2cTransport(self.reactor, proto, self.adaptor, [i2c_address for i2c_address, device_info in self.addresses])
