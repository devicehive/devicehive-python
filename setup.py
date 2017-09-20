from setuptools import setup
try:
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst')
except(IOError, ImportError):
    long_description = open('README.md').read()


setup(name='devicehive',
      version='2.0.2',
      author='DataArt (http://dataart.com)',
      author_email='info@devicehive.com',
      url='https://devicehive.com',
      license='Apache License 2.0',
      description='DeviceHive Python connectivity library',
      long_description=long_description,
      keywords='iot cloud m2m gateway embedded devicehive',
      packages=['devicehive', 'devicehive.data_formats', 'devicehive.handlers',
                'devicehive.transports'],
      install_requires=['websocket-client>=0.44.0', 'requests>=2.18.1',
                        'six>=1.10.0'])
