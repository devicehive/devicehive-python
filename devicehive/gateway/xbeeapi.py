# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

import struct

FRAME_DELIMETER = 0x7e
ESCAPE_PREFIX   = 0x7d
ESCAPE_XOR      = 0x20
ESCAPE_VALUES   = (0x11, 0x13, FRAME_DELIMETER, ESCAPE_PREFIX)

MULTICAST_NET_ADDR  = 0xfffe
MULTICAST_DEST_ADDR = 0x000000000000ffff


PACKET_OPTION_ACK       = 0x01
PACKET_OPTION_BROADCAST = 0x02
PACKET_OPTION_ENCRYPTED = 0x20
PACKET_OPTION_ENDDEVICE = 0x40
PACKET_OPTION_DESCR     = {PACKET_OPTION_ACK: "Packet Ack",
                 PACKET_OPTION_BROADCAST: "Packet was a broadcast packet",
                 PACKET_OPTION_ENCRYPTED: "Packet encrypted",
                 PACKET_OPTION_ENDDEVICE: "Packet was sent from an end deviec"}


REMOTE_AT_CMD_STATUS_OK = 0x00
REMOTE_AT_CMD_STATUS_ERROR = 0x01
REMOTE_AT_CMD_STATUS_INV_COMMAND = 0x02
REMOTE_AT_CMD_STATUS_INV_PARAMETER = 0x03
REMOTE_AT_CMD_STATUS_TRANSMISSION_FAILED = 0x04
REMOTE_AT_CMD_STATUS_DESCR = {REMOTE_AT_CMD_STATUS_OK: "OK",
                              REMOTE_AT_CMD_STATUS_ERROR: "ERROR",
                              REMOTE_AT_CMD_STATUS_INV_COMMAND: "Invalid Command",
                              REMOTE_AT_CMD_STATUS_INV_PARAMETER: "Invalid Parameter",
                              REMOTE_AT_CMD_STATUS_TRANSMISSION_FAILED: "Remote Command Tx Failure"}


DELIVERY_STATUS_OK = 0x00
DELIVERY_STATUS_MAC_ACK_FAILURE = 0x01
DELIVERY_STATUS_CCA_FAILURE = 0x02
DELIVERY_STATUS_INVALID_DESTINATION = 0x15
DELIVERY_STATUS_NET_ACK_FAILURE = 0x21
DELIVERY_STATUS_NOT_JOINED = 0x22
DELIVERY_STATUS_SELF_ADDR = 0x23
DELIVERY_STATUS_ADDR_NOT_FOUND = 0x24
DELIVERY_STATUS_ROUTE_NOT_FOUND = 0x25
DELIVERY_STATUS_BROADCAST_FAILURE = 0x26
DELIVERY_STATUS_INVALID_BINDING_TABLE_INDEX = 0x2b
DELIVERY_STATUS_RESOURCE_ERR = 0x2c
DELIVERY_STATUS_APS_TX = 0x2d
DELIVERY_STATUS_APS_TX2 = 0x2e
DELIVERY_STATUS_RESOURCE_ERR2 = 0x32
DELIVERY_STATUS_PAYLOAD_TOO_LARGE = 0x74
DELIVERY_STATUS_INDIRECT_MSG = 0x75


def escape_data(data) :
    """
    Replace special characters with escape sequence.
    """
    global ESCAPE_PREFIX, ESCAPE_XOR, ESCAPE_VALUES
    return bytearray([item for sublist in [(ESCAPE_PREFIX, i ^ ESCAPE_XOR) if i in ESCAPE_VALUES else (i,) for i in data] for item in sublist])


def unescape_data(data) :
    """
    Replace escape sequences with original values.
    """
    global ESCAPE_PREFIX, ESCAPE_XOR
    result = []
    i = 0
    data_len = len(data) - 1
    while i < data_len :
        if data[i] == ESCAPE_PREFIX :
            result.append(data[i + 1] ^ ESCAPE_XOR)
            i += 2
        else :
            result.append(data[i])
            i += 1
    if data_len >= 0 :
        result.append(data[data_len])
    return result


def array_to_hexstr(data, sep = "") :
    return reduce(lambda x, y: x + sep + y, ["%02X" % b for b in data], "")


class ApiFrame(object):
    def __init__(self, frame_id, escape) :
        self._frame_id = frame_id
        self._escape = escape

    def frame_type(self):
        raise NotImplemented()

    def payload(self):
        raise NotImplemented()

    def get_bytes(self) :
        payload = self.payload()
        data = bytearray(struct.pack("!HBB", len(payload) + 2, self.frame_type(), self._frame_id))
        data.extend(payload)
        data.append(0xff - ((sum(payload) + self.frame_type() + self._frame_id) & 0xff))
        if self._escape :
            data = escape_data(data)
        data.insert(0, FRAME_DELIMETER)
        return data

    def __str__(self) :
        return "Frame Id: {0:02X}; Payload: [{1:s}];".format(self._frame_id, array_to_hexstr(self.payload(), " "))


class TransmitPacketFrame(ApiFrame):
    def __init__(self, frame_id, escape, dest_addr = MULTICAST_DEST_ADDR, net_addr = MULTICAST_NET_ADDR, radius = 0, option = PACKET_OPTION_ACK, message = "") :
        super(TransmitPacketFrame, self).__init__(frame_id, escape)
        self._dest_addr = dest_addr
        self._net_addr = net_addr
        self._radius = radius
        self._option = option
        self._message = message
    def frame_type(self) :
        return 0x10
    def payload(self) :
        res = bytearray(self.dest_addr())
        res.extend( bytearray(self.net_addr()) )
        res.append(self._radius)
        res.append(self._option)
        res.extend(self._message)
        return res
    def dest_addr(self) :
        return (((self._dest_addr >> 56) & 0xff),
                    ((self._dest_addr >> 48) & 0xff),
                    ((self._dest_addr >> 40) & 0xff),
                    ((self._dest_addr >> 32) & 0xff),
                    ((self._dest_addr >> 24) & 0xff),
                    ((self._dest_addr >> 16) & 0xff),
                    ((self._dest_addr >> 8) & 0xff),
                    (self._dest_addr & 0xff))
    def net_addr(self) :
        return ((self._net_addr >> 8) & 0xff,  self._net_addr & 0xff)
    message = property(fget = lambda self : self._message)
    def __str__(self) :
        opt = "0x{0:02x}".format(self._option)
        if PACKET_OPTION_DESCR.has_key(self._option) :
            opt = PACKET_OPTION_DESCR[self._option]
        return "Tx Packet Dest Addr: {0:s}; Net Addr: {1:s}; Radius: {2:d}; Options: {3};".format( array_to_hexstr(self.dest_addr()), array_to_hexstr(self.net_addr()), self._radius, opt)


class ApiResponseFrame(object):
    def __init__(self, frame_data):
        self._frame_data = frame_data


class UnknownResponseFrame(ApiResponseFrame):
    def __init__(self, frame_data) :
        super(UnknownResponseFrame, self).__init__(frame_data)
    def frame_data():
        def fget(self) :
            return self._frame_data
        return locals()
    frame_data = property(**frame_data())
    def __str__(self):
        return "Unknown Frame Type: [{0:s}];".format( array_to_hexstr(self._frame_data, " ") )


class PacketResponseFrame(ApiResponseFrame) :
    FRAME_TYPE = 0x90
    def __init__(self, frame_data) :
        super(PacketResponseFrame, self).__init__(frame_data)
        self._src_addr = frame_data[1:9]
        self._net_addr = frame_data[9:11]
        self._options = frame_data[11]
        self._data = frame_data[12:]
    def __str__(self):
        options = "{0:02x}".format(self._options)
        if PACKET_OPTION_DESCR.has_key(self._options) :
            options = PACKET_OPTION_DESCR[self._options]
        return "Packet Src Addr: {0:s}; Net Addr: {1:s}; Options: {2:s}; Data: {3:s}".format(array_to_hexstr(self._src_addr), array_to_hexstr(self._net_addr), options, array_to_hexstr(self._data))


class AtCommandResponseFrame(ApiResponseFrame):
    FRAME_TYPE = 0x88

    OK = 0
    ERROR = 1
    INVALID_COMMAND = 2
    INVALID_PARAMETER = 3
    TX_FAILURE = 4

    status_descr = ("OK", "ERROR", "Invalid command", "Invalid parameter", "TX failure")

    def __init__(self, frame_data) :
        super(AtCommandResponseFrame, self).__init__(frame_data)
        self._frame_id   = frame_data[1]
        self._at_command = chr(frame_data[2]) + chr(frame_data[3])
        self._cmd_status = frame_data[4]
        self._cmd_data   = frame_data[5:]
    command = property(fget = lambda self : self._at_command)
    status = property(fget = lambda self : self._cmd_status)
    data = property(fget = lambda self : self._cmd_data)
    def __str__(self) :
        return "Frame Id: {0:02x}; AT{1:s} {2:s}; Status: {3:s};".format(self._frame_id,
            self._at_command, array_to_hexstr(self._cmd_data),
            AtCommandResponseFrame.status_descr[self._cmd_status])


class RemoteAtCommandResponseFrame(ApiResponseFrame):
    FRAME_TYPE = 0x97
    def __init__(self, frame_data) :
        super(RemoteAtCommandResponseFrame, self).__init__(frame_data)
        self._frame_id = frame_data[1]
        self._src_addr = frame_data[2:10]
        self._net_addr = frame_data[10:12]
        self._at_command = chr(frame_data[12]) + chr(frame_data[13])
        self._command_status = frame_data[14]
        self._command_data = frame_data[15:]
    def __str__(self):
        sts = "0x{0:02x}".format(self._command_status)
        if REMOTE_AT_CMD_STATUS_DESCR.has_key(self._command_status) :
            sts = REMOTE_AT_CMD_STATUS_DESCR[self._command_status]
        return "Remote AT Response: {0:s}; Status: {1:s}; Src Addr: {2:s}; Net Addr: {3:s}; Data: {4:s}".format(self._at_command, sts, array_to_hexstr(self._src_addr), array_to_hexstr(self._net_addr), array_to_hexstr(self._command_data))


class TransmitStatusResponseFrame(ApiResponseFrame):
    FRAME_TYPE = 0x8b
    DELIVERY_STATUS = {0x00: "Success", 0x01: "MAC ACK Failure", 0x02: "CCA Failure", 0x15: "Invalid destination endpoint", 0x21: "Network ACK Failure", 0x22: "Not Joined to Network", 0x23: "Self-addressed", 0x24: "Address Not Found", 0x25: "Route Not Found", 0x26: "Broadcast source failed to hear a neighbor relay the message", 0x2b: "Invalid binding table index", 0x2c: "Resource error lack of free buffers, timers", 0x2d: "Attempted broadcast with APS transmission", 0x2e: "Attempted unicast with APS transmission, but EE = 0", 0x32: "Resource error lack of free buffers, timers", 0x74: "Data payload too large", 0x75: "Indirect message unrequested"}
    DISCOVERY_STATUS = {0x00: "No Discovery Overhead", 0x01: "Address Discovery", 0x02: "Route Discovery", 0x03: "Route Discovery", 0x40: "Extended Timeout Discovery"}

    def __init__(self, frame_data):
        super(TransmitStatusResponseFrame, self).__init__(frame_data)
        # frame_id, net_addr, trans_retry, delivery_status, discovery_status
        self._frame_id = frame_data[1]
        self._net_addr = ((frame_data[2] << 8) & 0xff00) | (frame_data[3] & 0xff)
        self._transmit_retry = frame_data[4]
        self._delivery_status = frame_data[5]
        self._discovery_status = frame_data[6]
    delivery_status = property(fget = lambda self : self._delivery_status)
    def __str__(self):
        delivery = "0x{0:02x}".format(self._delivery_status)
        if TransmitStatusResponseFrame.DELIVERY_STATUS.has_key(self._delivery_status) :
            delivery = TransmitStatusResponseFrame.DELIVERY_STATUS[self._delivery_status]
        discovery = "0x{0:02x}".format(self._discovery_status)
        if TransmitStatusResponseFrame.DISCOVERY_STATUS.has_key(self._discovery_status) :
            discovery = TransmitStatusResponseFrame.DISCOVERY_STATUS[self._discovery_status]
        return "Tx Status; Frame ID: {0:02x}; Address: {1:04x}; Retries: {2:d}; {3:s}; {4:s};".format(self._frame_id, self._net_addr, self._transmit_retry, delivery, discovery)


class FrameError(Exception) :
    def __init__(self, msg, frame_data) :
        super(FrameError, self).__init__(msg)
        self.frame_data = frame_data
    def __repr__(self) :
        return array_to_hexstr(self.frame_data)


class FrameCrcError(FrameError) :
    def __init__(self, frame_data) :
        super(FrameCrcError, self).__init__('Invalid CRC. Frame: [{0:s}]'.format(array_to_hexstr(frame_data, ' ')), frame_data)


class MalformedFrameError(FrameError) :
    def __init__(self, frame_data) :
        super(MalformedFrameError, self).__init__('Malformed frame: [{0:s}].'.format(array_to_hexstr(frame_data, ' ')), frame_data)
        

class FrameFactory(object) :
    def __init__(self, escape = True):
        self._frame_id = 1
        self._escape = escape

    def _create(self, frame_type, frame_id, escape, *args, **kwargs):
        if not issubclass(frame_type, ApiFrame) :
            raise TypeError('Subclass of ApiFrame type expected.')
        return frame_type(frame_id, self._escape, *args, **kwargs)

    def create(self, frame_type, *args, **kwargs):
        frame = self._create(frame_type, self._frame_id, self._escape, *args, **kwargs)
        self._frame_id += 1
        if self._frame_id > 0xff :
            self._frame_id = 1
        return frame

    def create_without_response(self, frame_type, *args, **kwargs):
        return self._create(frame_type, 0x00, self._escape, *args, **kwargs)

    def _next_frame_data(self, buff) :
        # prefix, length, frame_type and crc bytes are mandatory
        if len(buff) < 4 :
            return (None, buff)
        # the first byte has to be the frame delimeter
        if buff[0] != FRAME_DELIMETER :
            raise MalformedFrameError(buff)
        # skip frame delimeter. frame delimeter should not be unescaped.
        data = buff[1:]
        if self._escape :
            data = unescape_data(data)
        # extract actual data
        payload_len = ((data[0] & 0xff) << 8) | (data[1] & 0xff)
        frame_len = payload_len + 3
        data_len = len(data)
        # if the frame in buffer is incomplete
        # if escaping enabled and CRC was escaped then the frame is incomplete (one more byte required in buffer to unescape CRC)
        if (data_len < frame_len) or (self._escape and data_len == frame_len and data[frame_len - 1] == ESCAPE_PREFIX) :
            return (None, buff)
        # current frame without frame delimeter
        rest = data[frame_len:]
        if len(rest) and self._escape :
            rest = escape_data(rest)
        return (data[:frame_len], bytearray(rest))

    def create_response(self, buffer) :
        frame_data, buff_rest = self._next_frame_data(buffer)
        if frame_data is None :
            return (None, buffer)
        payload_len = ((frame_data[0] & 0xff) << 8) | (frame_data[1] & 0xff)
        if payload_len < 2 :
            raise MalformedFrameError(frame_data)
        payload = frame_data[2:2 + payload_len]
        if 0xff != ((sum(payload) + frame_data[len(frame_data) - 1]) & 0xff) :
            raise FrameCrcError(buffer)
        # Decode payload
        frame_type = payload[0]
        frame_obj  = None
        if frame_type == AtCommandResponseFrame.FRAME_TYPE :
            frame_obj = AtCommandResponseFrame(payload)
        elif frame_type == TransmitStatusResponseFrame.FRAME_TYPE :
            frame_obj = TransmitStatusResponseFrame(payload)
        elif frame_type == PacketResponseFrame.FRAME_TYPE :
            frame_obj = PacketResponseFrame(payload)
        elif frame_type == RemoteAtCommandResponseFrame.FRAME_TYPE :
            frame_obj = RemoteAtCommandResponseFrame(payload)
        else :
            frame_obj = UnknownResponseFrame(frame_data)
        return (frame_obj, buff_rest)


class BaseRemoteAtCommandFrame(ApiFrame) :
    OPTION_DISABLE_ACK = 0x01
    OPTION_APPLY = 0x02
    OPTION_ET    = 0x04
    OPTION       = ("Disable Ack", "Auto Apply", "Extended Tx")
    def __init__(self, frame_id, escape, dest_addr = MULTICAST_DEST_ADDR, net_addr = MULTICAST_NET_ADDR, option = 0x02) :
        super(BaseRemoteAtCommandFrame, self).__init__(frame_id, escape)
        self._dest_addr = dest_addr
        self._net_addr = net_addr
        self._opt = option
    def payload(self):
        res = bytearray( self.dest_addr() )
        res.extend( bytearray(self.net_addr()) )
        res.append( self._opt )
        res.extend( bytearray(self.command()) )
        if self.has_argument() :
            res.extend(bytearray(self.argument()))
        return res
    def dest_addr(self):
        return (((self._dest_addr >> 56) & 0xff),
                    ((self._dest_addr >> 48) & 0xff),
                    ((self._dest_addr >> 40) & 0xff),
                    ((self._dest_addr >> 32) & 0xff),
                    ((self._dest_addr >> 24) & 0xff),
                    ((self._dest_addr >> 16) & 0xff),
                    ((self._dest_addr >> 8) & 0xff),
                    (self._dest_addr & 0xff))
    def net_addr(self):
        return ((self._net_addr >> 8) & 0xff, self._net_addr & 0xff)
    def opts(self) :
        return self._opt
    def frame_type(self):
        return 0x17
    def command(self):
        raise NotImplemented()
    def argument(self):
        raise NotImplemented()
    def has_argument(self):
        raise NotImplemented()
    def __str__(self):
        if self.has_argument() :
            return 'Frame Type: AT_REMOTE_COMMAND; Command: {1:s}; Argument: {2:s}; Dest Addr: {3:s}; Net Addr: {4:s}; Options: {5:s};'.format(self._frame_id, self.command(), self.argument(), array_to_hexstr(self.dest_addr()) , array_to_hexstr(self.net_addr()), BaseRemoteAtCommandFrame.OPTION[self._opt])
        else :
            return 'Frame Type: AT_REMOTE_COMMAND; Command: {1:s}; Dest Addr: {2:s}; Net Addr: {3:s}; Options: {4:s};'.format(self._frame_id, self.command(), array_to_hexstr(self.dest_addr()) , array_to_hexstr(self.net_addr()), BaseRemoteAtCommandFrame.OPTION[self._opt])


class RemoteMyCommandFrame(BaseRemoteAtCommandFrame) :
    def command(self):
        return "MY"
    def has_argument(self):
        return False


class RemoteAcCommandFrame(BaseRemoteAtCommandFrame) :
    def command(self):
        return "AC"
    def has_argument(self):
        return False


class RemoteDataCommandFrame(BaseRemoteAtCommandFrame):
    def __init__(self, frame_id, escape, dest_addr = MULTICAST_DEST_ADDR, net_addr = MULTICAST_NET_ADDR, option = 0x02, pin = 0, value = 4) :
        super(RemoteDataCommandFrame, self).__init__(frame_id, escape, dest_addr, net_addr, option)
        self._pin = pin
        self._value = value
    def command(self):
        return "D{0:d}".format(self._pin)
    def has_argument(self):
        return True
    def argument(self):
        return (self._value,)


class BaseAtCommandFrame(ApiFrame):
    """
    Used to query or set module parameters on the local device.
    """
    def __init__(self, frame_id, escape) :
        super(BaseAtCommandFrame, self).__init__(frame_id, escape)

    def payload(self):
        res = bytearray(self.command())
        if self.has_argument() :
            res.extend(bytearray(self.argument()))
        return res

    def frame_type(self):
        return 0x08

    def command(self) :
        raise NotImplemented()

    def has_argument(self):
        raise NotImplemented()

    def argument(self):
        raise NotImplemented()

    def __str__(self) :
        if self.has_argument() :
            return "Frame Type: AT_COMMAND; Command: {1:s}; Argument: {2:s};".format(self._frame_id, self.command(), self.argument())
        else :
            return "Frame Type: AT_COMMAND; Command: {1:s};".format(self._frame_id, self.command())


class VrCommandFrame(BaseAtCommandFrame):
    """
    Read firmware version of the module.
    """
    def __init__(self, frame_id, escape) :
        super(VrCommandFrame, self).__init__(frame_id, escape)
    def command(self) :
        return 'VR'
    def has_argument(self):
        return False


class AcCommandFrame(BaseAtCommandFrame):
    """
    Apply changes.
    Note, please, that this command should be issued
    after updating IO state.
    """
    def __init__(self, frame_id, escape) :
        super(VrCommandFrame, self).__init__(frame_id, escape)
    def command(self) :
        return 'AC'
    def has_argument(self):
        return False


class BaseAtHoldCommand(ApiFrame):
    def frame_type(self):
        return 0x09

