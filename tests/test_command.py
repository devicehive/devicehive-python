import unittest
import sys
from os import path
from zope.interface import implements


orig_name = __name__
orig_path = list(sys.path)
sys.path.insert(0, path.abspath(path.join(path.dirname(__file__), '..')))
try :
    devicehive = __import__('devicehive')
    __import__('devicehive.ws')
    __import__('devicehive.interfaces')
    __import__('devicehive.poll')
    __import__('devicehive.device.ws')
    ws = devicehive.ws
    dws = devicehive.device.ws
    poll = devicehive.poll
finally :
    sys.path[:] = orig_path
    __name__ = orig_name


class WsCommandTests(unittest.TestCase):
    def setUp(self):
        self.msg = {'action': 'command/insert', 'deviceGuid': '22345678-9012-3456-7890-123456789012', 'command': { 'id': 1, 'timestamp': None, 'userId': 2, 'command': 'cmd_name', 'parameters': [], 'lifetime': None, 'flags': 0, 'status': 'test status', 'result': None }}
    
    def test_interface(self):
        devicehive.interfaces.ICommand.implementedBy(dws.WsCommand)
    
    def test_create(self):
        ci = dws.WsCommand.create(self.msg)
        self.assertEquals(1, ci.id)
        self.assertEquals(2, ci.user_id)
        self.assertEquals(0, ci.flags)
        self.assertEquals('test status', ci.status)
    
    def test_to_dict(self):
        ci = dws.WsCommand.create(self.msg)
        d  = ci.to_dict()
        
        self.assertEquals(1, d['id'])
        self.assertEquals('cmd_name', d['command'])
        self.assertEquals(2, d['userId'])
        self.assertEquals([], d['parameters'])
        self.assertEquals(0, d['flags'])
        self.assertEquals('test status', d['status'])
        self.assertFalse('result' in d)
    
    def test__getter(self):
        ci = dws.WsCommand.create(self.msg)
        self.assertEquals('cmd_name', ci['command'])
        self.assertEquals([], ci['parameters']) 
        try :
            tmp = ci[123]
            self.fail('should raise TypeError')
        except TypeError :
            pass
        try :
            tmp = ci['test']
            self.fail('should raise IndexError')
        except IndexError :
            pass


class PollCommand(unittest.TestCase):
    def setUp(self) :
        self.message = {'id': 1, 'timestamp': None, 'userId': 2, 'command': 'cmdtest', 'parameters': [], 'lifetime': 123, 'flags': 4, 'status': 'status', 'result': 'result'}
    
    def test_getter(self):
        ci = poll.PollCommand.create(self.message)
        self.assertEquals('cmdtest', ci['command'])
        self.assertEquals([], ci['parameters'])
        try :
            tmp = ci[123]
            self.fail('should raise TypeError')
        except TypeError :
            pass
        try :
            tmp = ci['test']
            self.fail('should raise IndexError')
        except IndexError :
            pass
    
    def test_to_dict(self):
        ci = poll.PollCommand.create(self.message)
        self.assertEquals(1, ci.id)
        self.assertEquals(2, ci.user_id)
        self.assertEquals('cmdtest', ci.command)
        self.assertEquals([], ci.parameters)
        self.assertEquals(123, ci.lifetime)
        self.assertEquals(4, ci.flags)
        self.assertEquals('status', ci.status)
        self.assertEquals('result', ci.result)


if __name__ == '__main__':
    unittest.main()

