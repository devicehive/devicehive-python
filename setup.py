# -*- coding: utf-8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

from os import path
from sys import platform
try:
    from setuptools import setup
except:
    from distutils.core import setup
from distutils.sysconfig import get_python_lib


setup(
    name = 'devicehive',
    version = '0.0.2',
    author = 'DataArt Apps (http://dataart.com)',
    author_email = 'info@devicehive.com',
    url = 'http://devicehive.com',
    summary = 'DeviceHive - the framework for interfacing applications and devices with the web cloud',
    license = 'MIT',
    description = 'A framework for interfacing applications and devices with the web cloud',
    long_description = open('README.md').read(),
    keywords = "web cloud api embedded tutorial",
    packages = ['devicehive', 'devicehive.client', 'devicehive.device', 'devicehive.gateway'],
    install_requires = ['twisted', 'pyOpenSSL', 'service-identity'],
    requires = ['twisted (>=12.0)', 'pyOpenSSL (>=0.14)', 'service-identity (>=14.0.0)'],
    data_files=[(path.join(get_python_lib(), 'devicehive'),  ['LICENSE']),
                (path.join(get_python_lib(), 'devicehive', 'tests'), ['tests/test_binary.py']),
                (path.join(get_python_lib(), 'devicehive', 'tests'), ['tests/test_command.py']),
                (path.join(get_python_lib(), 'devicehive', 'tests'), ['tests/test_dhjson.py']),
                (path.join(get_python_lib(), 'devicehive', 'tests'), ['tests/test_proto.py']),
                (path.join(get_python_lib(), 'devicehive', 'tests'), ['tests/test_utils.py']),
                (path.join(get_python_lib(), 'devicehive', 'tests'), ['tests/test_wsdev.py']),
                (path.join(get_python_lib(), 'devicehive', 'tests'), ['tests/test_wsparser.py']),
                (path.join(get_python_lib(), 'devicehive', 'tests'), ['tests/test_wsproto.py']),
                (path.join(get_python_lib(), 'devicehive', 'tests'), ['tests/test_client_ws_factory.py']),
                (path.join(get_python_lib(), 'devicehive', 'examples'), ['examples/basic_gateway_example.py']),
                (path.join(get_python_lib(), 'devicehive', 'examples'), ['examples/client_example.py']),
                (path.join(get_python_lib(), 'devicehive', 'examples'), ['examples/ping_pong_example.py']),
                (path.join(get_python_lib(), 'devicehive', 'examples'), ['examples/ws_devicehive_example.py']),
                (path.join(get_python_lib(), 'devicehive', 'examples'), ['examples/raspi_led_thermo.py']),
                (path.join(get_python_lib(), 'devicehive', 'examples'), ['examples/virtual_led_example.py']),
                (path.join(get_python_lib(), 'devicehive', 'examples'), ['examples/virtual_led_example.cfg']),
                (path.join(get_python_lib(), 'devicehive', 'examples'), ['examples/rpi_example.py']),
                (path.join(get_python_lib(), 'devicehive', 'examples'), ['examples/basic_gateway_example.py']),
                (path.join(get_python_lib(), 'devicehive', 'examples'), ['examples/rpi_example.cfg'])]
)

