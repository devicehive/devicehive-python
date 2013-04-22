# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:
"""
Module provides one of many possible implementations of I2C protocol.
This implementation assumes that i2c slaves on the i2c bus are conform to
the specific interface:
    register 0x0c - Command register. Master is supposed to write command data into
                    this register.
    register 0x0d - Data register. Reading from this register returns current slave device buffer.
    register 0x0f - Flag register. If this register contains 0x00 value this means
                    that i2c slave does not have data to read. Master device has to
                    check this field before reading actual data and set to 0 if
                    data were obtained successfully. The slave device cannot generate
                    additional data if this flag is set.
"""

from threading import Event
from struct import pack
from thread import allocate_lock
from smbus import SMBus
from zope.interface import implements
from twisted.internet import reactor, threads, interfaces


__all__ = ['LOG_INFO', 'LOG_ERR', 'I2cTransport', 'I2cEndpoint',
           'I2C_REG_CMD', 'I2C_REG_DATA', 'I2C_REG_FLAG']


def LOG_INFO(msg):
    """
    Abstraction method for logging general purpose information.
    @type msg: C{str}
    @param msg: a message to be logged
    """
    print '[info]\t{0}'.format(msg)


def LOG_ERR(msg):
    """
    Abstraction method for logging errors.
    @type msg: C{str}
    @param msg: a error message to be logged.
    """
    print '[error]\t{0}'.format(msg)


I2C_REG_CMD = 0x0c
I2C_REG_DATA = 0x0d
I2C_REG_FLAG = 0x0f


class I2cTransport(object):
    """
    @ivar adaptor: i2c adaptor number to use
    @ivar poll_timeout: adaptor polling interval
    """

    implements(interfaces.ITransport)

    adaptor = 0
    poll_timeout = 10
    protocol = None

    def __init__(self, _reactor, protocol, adaptor, addresses, poll_timeout=10):
        """
        @param _reactor: reference to twisted reactor
        @param protocol: a C{twisted.internet.interfaces.IProtocol} protocol which handles i2c channel
        @param adaptor: C{int} adaptor number
        @param addresses: C{tuple} of i2c slaves addresses
        @param poll_timeout: C{int} polling timeout in seconds
        """
        self.adaptor = adaptor
        self.poll_timeout = poll_timeout
        self.bus = SMBus()
        self.addresses = addresses
        self.dest_address = -1
        self.is_stopped = Event()
        self.adaptor_lock = allocate_lock()

        def shutdown_handler():
            LOG_INFO('A request to shutdown twisted reactor has been received.')
            self.stop()
        _reactor.addSystemEventTrigger('before', 'shutdown', shutdown_handler)
        self.protocol = protocol
        self.protocol.makeConnection(self)

    def set_destination_device(self, index):
        """
        Method set destination address to be used with following write calls.
        @param index: an C{int} index of destination address
        """
        if not isinstance(index, int) and not isinstance(index, long):
            raise TypeError('int index expected')
        if index < 0 or index > len(self.addresses):
            raise ValueError('Addresses index is out of range.')
        self.dest_address = self.addresses[index]
        return self.dest_address

    def start(self):
        """
        Starts polling loop for specified adaptor.
        """
        def poll_func(adaptor_lock, is_stopped, bus, addresses, poll_timeout):
            """
            Actual polling loop.
            @param adaptor_lock: the code has to acquire the lock C{threading.Lock} before accessing i2c adaptor.
            @param is_stopped: a C{threading.Event} based flag which indicates that polling loop has be to terminated.
            @param bus: a reference to C{smbus.SMBus} object.
            @param addresses: C{tuple} of i2c addresses to poll.
            @param poll_timeout: C{int} polling timeout in seconds.
            """
            while not is_stopped.is_set():
                for address in addresses:
                    LOG_INFO('Reading data present flag from {0} i2c-slave.'.format(address))
                    flag = False
                    with adaptor_lock:
                        try:
                            flag = (bus.read_byte_data(address, I2C_REG_FLAG) != 0)
                        except IOError, err:
                            LOG_ERR('Failed to read FLAG REG in slave {0}. Reason: {1}.'.format(address, err))
                    if flag:
                        data = b''
                        num_data = ()
                        with adaptor_lock:
                            try:
                                num_data = bus.read_block_data(address, I2C_REG_DATA)
                            except IOError, err:
                                LOG_ERR('Failed to read data block from device {0}. Reason: {1}.'.format(address, err))
                        if len(num_data) > 0:
                            pack('B' * len(num_data), *num_data)
                        LOG_INFO('Reset data-ready flag in i2c-salve {0}.'.format(address))
                        with adaptor_lock:
                            try:
                                bus.write_byte_data(address, I2C_REG_FLAG, 0)
                            except IOError, err:
                                LOG_ERR('Failed to reset data-ready flag in i2c-slave {0}.'.format(address, err))
                        self.protocol.dataReceived((address, data))
                    LOG_INFO('Reading data from address {0}.'.format(address))
                LOG_INFO('Timeout value = {0}.'.format(poll_timeout))
                is_stopped.wait(poll_timeout)
        LOG_INFO('Opening I2C-{0} adaptor.'.format(self.adaptor))
        self.bus.open(self.adaptor)
        LOG_INFO('I2C-{0} adaptor has been opened.'.format(self.adaptor))
        LOG_INFO('Starting I2C-{0} adaptor polling thread.'.format(self.adaptor))
        reactor.callInThread(poll_func, self.adaptor_lock, self.is_stopped, self.bus, self.addresses, self.poll_timeout)

    def stop(self):
        """
        Stops polling loop if it is running.
        @return: C{threading.Event} object to allow callee to invoke it's wait() method.
        """
        if not self.is_stopped.is_set():
            self.is_stopped.set()
        return self.is_stopped

    def write(self, data):
        """
        Method writes data into selected i2c slave.
        @param data: C{str} to be sent into i2c slave.
        @return: C{twisted.internet.defer.Deferred}
        """
        if isinstance(data, str):
            raise TypeError('data should be of str type.')
        if 0 < self.dest_address >= len(self.addresses):
            raise ValueError('Destination address index is out of range.')

        def write_thread(adaptor_lock, bus, dest_address, data):
            """
            The thread dedicated to write data into i2c slave.
            @param adaptor_lock: C{threading.Lock}
            @param bus: a reference to C{smbus.SMBus} object.
            @param dest_address: C{int} which represents destination address
            @param data: a C{str} to be written into i2c slave.
            """
            LOG_INFO('Writing data into {0} i2c slave.'.format(dest_address))
            with adaptor_lock:
                bus.write_block_data(dest_address, I2C_REG_CMD, data.encode('utf-8'))
            LOG_INFO('The data has been successfully written into {0} i2c slave.'.format(dest_address))
        return threads.deferToThread(write_thread, self.adaptor_lock, self.bus, self.dest_address, data)

    def writeSequence(self, data_list):
        """
        Method writes list of string into i2c slave.
        @param data_list: a C{list} of strings to written into i2c slave register.
        """
        if not isinstance(data_list, list) and not isinstance(data_list, tuple):
            raise TypeError('data should be of list or tuple type.')
        if 0 < self.dest_address >= len(self.addresses):
            raise ValueError('Destination address index is out of range.')

        def write_thread(adaptor_lock, bus, dest_address, data_list):
            """
            This thread writes strings into i2c slave.
            @param adaptor_lock: C{threading.Lock} object which arbiters access to I2C hardware.
            @param bus: a reference to C{smbus.SMBus} object.
            @param dest_address: a C{tuple} of addresses to poll.
            @param data_list: a C{list} of strings to send into i2c slave.
            """
            LOG_INFO('Writing list of string into i2c slave.'.format(dest_address))
            for item in data_list:
                with adaptor_lock:
                    bus.write_block_data(dest_address, I2C_REG_CMD, item.encode('utf-8'))
            LOG_INFO('A data has been written into i2c slave {0}.'.format(dest_address))
        return threads.deferToThread(write_thread, self.bus, self.dest_address, data_list)

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

    def __init__(self, reactor, adaptor, addresses, poll_timeout):
        self.reactor = reactor
        self.adaptor = adaptor
        self.addresses = addresses
        self.poll_timeout = poll_timeout

    def listen(self, proto_factory):
        proto = proto_factory.buildProtocol((self.adaptor, self.addresses))
        return I2cTransport(proto, self.adaptor, self.addresses, self.poll_timeout)
