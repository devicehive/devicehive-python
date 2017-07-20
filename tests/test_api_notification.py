from devicehive import DeviceException
from devicehive import ApiResponseException


def test_send(test):

    def handle_connect(handler):
        device_id = test.generate_id('send-notification')
        notification_name = test.generate_id('send-notification')
        device = handler.api.put_device(device_id)
        notification = device.send_notification(notification_name)
        assert notification.device_id() == device_id
        assert isinstance(notification.id(), int)
        assert notification.notification() == notification_name
        assert not notification.parameters()
        assert notification.timestamp()
        parameters = 'parameters'
        notification = device.send_notification(notification_name,
                                                parameters=parameters)
        assert notification.device_id() == device_id
        assert isinstance(notification.id(), int)
        assert notification.notification() == notification_name
        assert notification.parameters() == parameters
        assert notification.timestamp()
        device_1 = handler.api.get_device(device_id)
        device.remove()
        try:
            device.send_notification(notification_name)
            assert False
        except DeviceException:
            pass
        try:
            device_1.send_notification(notification_name)
            assert False
        except ApiResponseException as api_response_exception:
            # TODO: uncomment after server response will be fixed.
            # assert api_response_exception.code() == 404
            pass

    test.run(handle_connect)
