#!/usr/bin/env python

import sys

from twisted.python import log
from twisted.internet import reactor, task
from zope.interface import implements

import devicehive
import devicehive.auto


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
        return (devicehive.Equipment(name='ThermoSensor', code='therm', type='Thermo sensor'), )
    
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

    def __init__(self):
        super(App, self).__init__()
        self.info = SnrEdrInfo()
        self.cmd_gen = cmdgen.CommandGenerator()

    def on_apimeta(self, websocket_server, server_time):
        log.msg('API metadata has been received.')

    def read_thermometr(self):
        log.msg('Read thermometr.')

        error_indication, errorStatus, errorIndex, varBinds = self.cmd_gen.getCmd(
                cmdgen.CommunityData('public'),
                cmdgen.UdpTransportTarget(('demo.snmplabs.com', 161)),
                cmdgen.MibVariable('SNMPv2-MIB', 'sysName', 0)
        )

        if error_indication:
            log.err('Failed to read themperature. Reason: {0}.'.format(error_indication))
        else:
            if errorStatus:
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

        task.LoopingCall(self.read_thermometr).start(1)

        def on_subscribe(result) :
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
    return dict()


def main():
    log.startLogging(sys.stdout)

    args = parse_arguments()

    connection = devicehive.auto.AutoFactory(App(**args))
    connection.connect(_API_URL)   

    reactor.run()


if __name__ == '__main__' :
    main()

