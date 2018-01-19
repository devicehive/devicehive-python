# Copyright (C) 2018 DataArt
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================


import glob
import hashlib
import sched
import time
import threading
from devicehive import Handler
from devicehive import DeviceHive

SERVER_URL = 'http://playground.devicehive.com/api/rest'
SERVER_REFRESH_TOKEN = 'eyJhbGciOiJIUzI1NiJ9.eyJwYXlsb2FkIjp7InVzZXJJZCI6MTAsImFjdGlvbnMiOlsiR2V0TmV0d29yayIsIkdldERldmljZSIsIkdldERldmljZVN0YXRlIiwiR2V0RGV2aWNlTm90aWZpY2F0aW9uIiwiR2V0RGV2aWNlQ29tbWFuZCIsIkdldERldmljZUNsYXNzIiwiUmVnaXN0ZXJEZXZpY2UiLCJDcmVhdGVEZXZpY2VOb3RpZmljYXRpb24iLCJDcmVhdGVEZXZpY2VDb21tYW5kIiwiVXBkYXRlRGV2aWNlQ29tbWFuZCIsIkdldEN1cnJlbnRVc2VyIiwiVXBkYXRlQ3VycmVudFVzZXIiLCJNYW5hZ2VUb2tlbiJdLCJuZXR3b3JrSWRzIjpbIjEwIl0sImRldmljZUlkcyI6WyIqIl0sImV4cGlyYXRpb24iOjE1MzU4MDMxNDMzMTQsInRva2VuVHlwZSI6IlJFRlJFU0gifX0.5qgXmEZTvnMlMjByGGhcxpfD0s_TSFM3cAQKoo22Ees' # 'PUT_YOUR_REFRESH_TOKEN_HERE'
DEVICE_ID = 'raspi-led-thermo-' \
            + hashlib.md5(SERVER_REFRESH_TOKEN.encode()).hexdigest()[0:8]
LED_PIN = 17


''' Real or fake GPIO handler.
'''
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
except ImportError:
    class FakeGPIO(object):
        OUT = "OUT"

        def __init__(self):
            print('Fake gpio initialized')

        def setup(self, io, mode):
            print('Set gpio {0}; Mode: {1};'.format(io, mode))

        def output(self, io, vlaue):
            print('Set gpio {0}; Value: {1};'.format(io, vlaue))

    GPIO = FakeGPIO()


''' Temperature sensor wrapper. Gets temperature readings form file.
'''
class TempSensor(object):
    def __init__(self):
        files = glob.glob('/sys/bus/w1/devices/28-*/w1_slave')
        if len(files) > 0:
            self.file_name = files[0]
        else:
            self.file_name = None
        self.last_good_temp = 0.0

    def get_temp(self):
        if self.file_name is None:
            return self.last_good_temp
        with open(self.file_name) as f:
            content = f.readlines()
            for line in content:
                # sometimes CRC is bad, so we will return last known good temp
                if line.find('crc=') >= 0 and line.find('NO') >= 0:
                    return self.last_good_temp
                p = line.find('t=')
                if p >= 0:
                    self.last_good_temp = float(line[p+2:]) / 1000.0
                    return self.last_good_temp
        return self.last_good_temp


class SampleHandler(Handler):
    INTERVAL_SECONDS = 5

    def __init__(self, api, device_id=DEVICE_ID):
        super(SampleHandler, self).__init__(api)
        self._device_id = device_id
        self._device = None
        self._sensor = TempSensor()
        self._scheduler = sched.scheduler(time.time, time.sleep)
        GPIO.setup(LED_PIN, GPIO.OUT)
        GPIO.output(LED_PIN, 0)
        print('DeviceId: ' + self._device_id)

    def _timer_loop(self):
        t = self._sensor.get_temp()
        self._device.send_notification('temperature', parameters={'value': t})
        self._scheduler.enter(self.INTERVAL_SECONDS, 1, self._timer_loop, ())

    def handle_connect(self):
        self._device = self.api.put_device(self._device_id)
        self._device.subscribe_insert_commands()
        print('Connected')
        self._timer_loop()
        t = threading.Thread(target=self._scheduler.run)
        t.setDaemon(True)
        t.start()

    def handle_command_insert(self, command):
        if command.command == 'led/on':
            GPIO.output(LED_PIN, 1)
            command.status = "Ok"
        elif command.command == 'led/off':
            GPIO.output(LED_PIN, 0)
            command.status = "Ok"
        else:
            command.status = "Unknown command"
        command.save()


dh = DeviceHive(SampleHandler)
dh.connect(SERVER_URL, refresh_token=SERVER_REFRESH_TOKEN)
