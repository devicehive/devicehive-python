#!/usr/bin/env python

import sys

import argparse

from pysnmp.entity.rfc3413.oneliner import cmdgen
from twisted.python import log
from twisted.internet import reactor, task
from zope.interface import implements

import devicehive
import devicehive.auto



SNMP_COMMUNITY = cmdgen.CommunityData('public', mpModel=0)

SYS_NAME_MIB = cmdgen.MibVariable('SNMPv2-MIB', 'sysName', 0)
SYS_DESCR_MIB = cmdgen.MibVariable('SNMPv2-MIB', 'sysDescr', 0)

OBJ_ID_MIB = cmdgen.MibVariable('SNMPv2-SMI', 'enterprises', 40418, 2, 2)
TEMPERATURE_MIB = cmdgen.MibVariable('SNMPv2-SMI', 'enterprises', 40418, 2, 2, 4, 1)


class SnmpError(Exception):

    def __init__(self, error_status, error_index):
        self.status = error_status
        self.index = error_index

    def __repr__(self):
        return '<{}(error_status: {}, error_index: {})>'.format(
            self.__class__.__name__, self.status, self.index
        )


def read_snmp(snmp_host, snmp_port, mib):
    cmd_gen = cmdgen.CommandGenerator()

    error_indication, error_status, error_index, var_binds = cmd_gen.getCmd(
        SNMP_COMMUNITY,
        cmdgen.UdpTransportTarget((snmp_host, snmp_port)),
        mib
    )

    if error_indication:
        raise IOError(error_indication)
    else:
        if error_status:
            raise SnmpError(error_status, error_index and var_binds[int(error_index) - 1] or '?')
        else:
            name, value = var_binds[0]
            return value


def read_temperature(snmp_host, snmp_port):
    return int(read_snmp(snmp_host, snmp_port, TEMPERATURE_MIB))


class SensorInfo(object):
    implements(devicehive.interfaces.IDeviceInfo)

    def __init__(self, ip, name, descr):
        self.__ip = ip
        self.__name = name
        self.__descr = descr

    @property
    def id(self):
        return 'a2345678-1f8f-11e2-8979-c42c030dd6a5'
    
    @property
    def key(self):
        return 'SENSOR'

    @property
    def name(self):
        return '%s (%s)' % (self.__name, self.__ip)
    
    @property
    def status(self):
        return 'Online'
    
    @property
    def network(self):
        return devicehive.Network(key='Netname', name='fridge-net', descr='main station')
    
    @property
    def device_class(self):
        return devicehive.DeviceClass(name=self.__name, version=self.__descr, is_permanent=False)
    
    @property
    def equipment(self):
        return [devicehive.Equipment(name='therm', code='therm', type='therm'), ]
    
    @property
    def data(self):
        return None

    def to_dict(self):
        res = {
            'key': self.key,
            'name': self.name
        }

        if self.status is not None:
            res['status'] = self.status
   
        if self.network is not None:
            res['network'] = self.network.to_dict() if devicehive.interfaces.INetwork.implementedBy(self.network.__class__) else self.network
            res['deviceClass'] = self.device_class.to_dict() if devicehive.interfaces.IDeviceClass.implementedBy(self.device_class.__class__) else self.device_class

        if self.equipment is not None:
            res['equipment'] = [x.to_dict() for x in self.equipment]

        return res

    def __repr__(self):
        return '<SensorInfo({}, {})>'.format(self.__name, self.__descr)


class App(object):
    implements(devicehive.interfaces.IProtoHandler)

    def __init__(self, info, snmp_host, snmp_port, update_interval, **kwargs):
        super(App, self).__init__()
        self.info = info
        self.snmp_host = snmp_host
        self.snmp_port = snmp_port
        self.update_interval = update_interval

    def on_apimeta(self, websocket_server, server_time):
        log.msg('API metadata has been received.')

    def read_thermometr(self):
        log.msg('Read thermometr data.')

        try:
            temperature = read_temperature(self.snmp_host, self.snmp_port)

            log.msg('Current temperature reading is: {}.'.format(temperature))

            self.factory.notify('temperature', {
                'equipment': 'ThermoSensor',
                'value': temperature
            }, device_id=self.info.id, device_key=self.info.key)

        except IOError as err:
            log.err('Failed to read current temperature. Reason: {}.'.format(err))
        except SnmpError as snmp_err:
            log.err('Snmp error on temperature read. Reason: {}.'.format(snmp_err))

    def on_connected(self):
        log.msg('Connected to devicehive server.')

        def on_subscribe(result) :
            task.LoopingCall(self.read_thermometr).start(self.update_interval, now=True)
            self.factory.subscribe(self.info.id, self.info.key)

        def on_failed(reason) :
            log.err('Failed to save device {0}. Reason: {1}.'.format(self.info, reason))
            self.connected = False

        self.factory.device_save(self.info).addCallbacks(on_subscribe, on_failed)
    
    def on_connection_failed(self, reason) :
        log.err('Failed to connect to devicehive.')
    
    def force_update(self, finish_cb):
        self.read_thermometr()
        finish_cb.callback(devicehive.CommandResult('Completed'))

    def on_command(self, device_id, command, finished):
        if command.command == 'update':
            self.force_update(finished)
        else :
            log.err('Unsupported command {0} received.'.format(command))
            finished.errback()

    def on_closing_connection(self):
        pass

    def on_failure(self, device_id, reason):
        pass


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument('--url', dest='url', action='store', required=True)
    parser.add_argument('--sensor-host', dest='sensor_host', action='store', required=True)
    parser.add_argument('--sensor-port', dest='sensor_port', action='store', default=161)
    parser.add_argument('--update-interval', dest='update_interval', action='store', default=10)

    options = parser.parse_args()

    return options


def get_sensor_info(snmp_host, snmp_port):
    try:
        sys_name = str(read_snmp(snmp_host, snmp_port, SYS_NAME_MIB))
        sys_descr = str(read_snmp(snmp_host, snmp_port, SYS_DESCR_MIB))
    
        return SensorInfo(snmp_host, sys_name, sys_descr)
    except IOError as err:
        log.err('Failed to read SNMP sensor data. Reason: {}'.format(err))
        exit(-1)
    except SnmpError as snmp_err:
        log.err('SNMP error: {}.'.format(snmp_err))
        exit(-1)


def main():
    options = parse_arguments()

    log.startLogging(sys.stdout)
    log.msg('Using devicehive {}, sensor {}:{}.'.format(options.url, options.sensor_host, options.sensor_port))

    info = get_sensor_info(options.sensor_host, int(options.sensor_port))
    log.msg('Serving sensor {}.'.format(info))

    log.msg('Connecting to devicehive server...')
    connection = devicehive.auto.AutoFactory(App(info, options.sensor_host, int(options.sensor_port), options.update_interval))
    connection.connect(options.url)
    reactor.run()

    log.msg('Application closed.')


if __name__ == '__main__' :
    main()

