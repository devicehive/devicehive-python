import unittest
import sys
from os import path
from zope.interface import implements


orig_name = __name__
orig_path = list(sys.path)
sys.path.insert(0, path.abspath(path.join(path.dirname(__file__), '..', '..')))
try :
    devicehive = __import__('devicehive')
    __import__('devicehive.ws')
    ws = devicehive.ws
finally :
    sys.path[:] = orig_path
    __name__ = orig_name


class WsCommandTests(unittest.TestCase):
    def setUp(self):
        self.msg = {'action': 'command/insert', 'deviceGuid': '22345678-9012-3456-7890-123456789012', 'command': { 'id': 1, 'timestamp': None, 'userId': 2, 'command': 'cmd_name', 'parameters': [], 'lifetime': None, 'flags': 0, 'status': 'test status', 'result': None }}
    
    def test_create_from(self):
        ci = ws.WsCommand.create_from_ci(self.msg)
        self.assertEquals(1, ci.id)
        self.assertEquals(2, ci.user_id)
        self.assertEquals(0, ci.flags)
        self.assertEquals('test status', ci.status)
    
    def test_to_dict(self):
        ci = ws.WsCommand.create_from_ci(self.msg)
        d  = ci.to_dict()
        
        self.assertEquals(1, d['id'])
        self.assertEquals('cmd_name', d['command'])
        self.assertEquals(2, d['userId'])
        self.assertEquals([], d['parameters'])
        self.assertEquals(0, d['flags'])
        self.assertEquals('test status', d['status'])
        self.assertFalse('result' in d)
    
    def test__getter(self):
        ci = ws.WsCommand.create_from_ci(self.msg)
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


if __name__ == '__main__':
    unittest.main()

