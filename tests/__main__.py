# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:


import unittest

testmodules = ('test_binary', 'test_command', 'test_proto', 'test_utils', 'test_wsparser', 'test_wsproto', 'test_wsdev', 'test_dhjson')

suite = unittest.TestSuite()
for t in testmodules:
    suite.addTest(unittest.defaultTestLoader.loadTestsFromName(t))
unittest.TextTestRunner().run(suite)

