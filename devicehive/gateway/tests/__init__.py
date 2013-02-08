# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8 encoding=utf-8:


import unittest


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    tests = unittest.defaultTestLoader.discover('.')
    for testsuite in tests :
        runner.run(testsuite)
