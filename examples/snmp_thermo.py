#!/usr/bin/env python

import sys

from pysnmp.entity.rfc3413.oneliner import cmdgen
from twisted.python import log
from twisted.internet import reactor, task
from zope.interface import implements

import devicehive
import devicehive.auto


# MIB_VARIABLE = ('SNMPv2-MIB', 'sysName', 0)
MIB_VARIABLE = ('SNMPv2-MIB', 'snmpInPkts', 0)
UPDATE_INTERVAL = 10


class SnrEdrInfo(object):
    implements(devicehive.interfaces.IDeviceInfo)

    @property
    def id(self):
        return '12345678-1f8f-11e2-8979-c42c030dd6a5'
    
    @property
    def key(self):
        return 'SNR_ERD'

    @property
    def name(self):
        return 'SNR_ERD'
    
    @property
    def status(self):
        return 'Online'
    
    @property
    def network(self):
        return devicehive.Network(key='Netname', name='FredgeNet', descr='Main Station Fredge Network')
    
    @property
    def device_class(self):
        return devicehive.DeviceClass(name='SNR_EDR', version='1.0', is_permanent=False)
    
    @property
    def equipment(self):
        return [devicehive.Equipment(name='ThermoSensor', code='therm', type='ThermoSensor'), ]
    
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


class App(object):
    implements(devicehive.interfaces.IProtoHandler)

    def __init__(self, snmp_host='demo.snmplabs.com', snmp_port=161, snmp_community='public', **kwargs):
        super(App, self).__init__()
        self.info = SnrEdrInfo()
        self.cmd_gen = cmdgen.CommandGenerator()
        self.snmp_server = (snmp_host, snmp_port)
        self.snmp_community = snmp_community

    def on_apimeta(self, websocket_server, server_time):
        log.msg('API metadata has been received.')

    def read_thermometr(self):
        log.msg('Read thermometr data.')

        error_indication, error_status, error_index, var_binds = self.cmd_gen.getCmd(
                cmdgen.CommunityData(self.snmp_community),
                cmdgen.UdpTransportTarget(self.snmp_server),
                cmdgen.MibVariable(*MIB_VARIABLE)
        )

        if error_indication:
            log.err('Failed to read themperature. Reason: {0}.'.format(error_indication))
        else:
            if error_status:
                log.err('%s at %s' % (
                    error_status.prettyPrint(),
                    error_index and var_binds[int(error_index) - 1] or '?'
                ))
            else:
                log.msg('Data has been received from the SNMP server.')
                for name, val in var_binds:
                    log.msg('%s = %s' % (name.prettyPrint(), val.prettyPrint()))
                    self.factory.notify('themperature', {
                        'equipment': 'ThermoSensor',
                        'value': val.prettyPrint()
                    }, device_id=self.info.id, device_key=self.info.key)

    def on_connected(self):
        log.msg('Connected to devicehive server.')

        def on_subscribe(result) :
            task.LoopingCall(self.read_thermometr).start(UPDATE_INTERVAL, now=True)
            self.factory.subscribe(self.info.id, self.info.key)

        def on_failed(reason) :
            log.err('Failed to save device {0}. Reason: {1}.'.format(self.info, reason))
            self.connected = False

        self.factory.device_save(self.info).addCallbacks(on_subscribe, on_failed)
    
    def on_connection_failed(self, reason) :
        log.err('Failed to connect to devicehive.')
    
    def force_update(self, finish_cb):
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
    return {
        'devicehive_url': 'http://ec2-54-88-181-211.compute-1.amazonaws.com:8080/DeviceHiveJava-1.3.0.0-SNAPSHOT/rest', # 'http://test001.cloud.devicehive.com/devicehive-test001/rest',
        'snmp_host': 'demo.snmplabs.com',
        'snmp_port': 161,
        'snmp_community': 'public'
    }


def main():
    log.startLogging(sys.stdout)

    params = parse_arguments()

    connection = devicehive.auto.AutoFactory(App(**params))
    connection.connect(params.get('devicehive_url'))

    reactor.run()


if __name__ == '__main__' :
    main()

