from os import path
from sys import platform
try:
    from setuptools import setup
except:
    from distutils.core import setup
from distutils.sysconfig import get_python_lib


setup (
    name = 'devicehive',
    version = '0.0.1',
    author = 'DataArt Apps (http://dataart.com)',
    author_email = 'info@devicehive.com',
    url = 'http://devicehive.com',
    summary = 'DeviceHive - the framework for interfacing applications and devices with the web cloud',
    license = 'MIT',
    description = 'A framework for interfacing applications and devices with the web cloud',
    long_description = open('README').read(),
    keywords = "web cloud api embedded tutorial",
    packages = ['devicehive', 'devicehive.test'],
    install_requires = ['twisted'],
    requires = ['twisted (>=12.0)'],
    data_files=[(path.join(get_python_lib(), 'devicehive'),  ['LICENSE']),
                (path.join(get_python_lib(), 'devicehive', 'examples'), ['examples/raspi_led_thermo.py']),
                (path.join(get_python_lib(), 'devicehive', 'examples'), ['examples/devicehive_example.py']),
                (path.join(get_python_lib(), 'devicehive', 'examples'), ['examples/virtual_led_example.py']),
                (path.join(get_python_lib(), 'devicehive', 'examples'), ['examples/virtual_led_example.cfg']),
                (path.join(get_python_lib(), 'devicehive', 'examples'), ['examples/rpi_example.py']),
                (path.join(get_python_lib(), 'devicehive', 'examples'), ['examples/rpi_example.cfg'])]
)
