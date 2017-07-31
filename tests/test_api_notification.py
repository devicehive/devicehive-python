from devicehive import DeviceError
from devicehive import ApiResponseError


def list_notifications(device, **params):
    notifications = device.list_notifications(**params)
    return [notification for notification in notifications
            if notification.notification[0] != '$']


def test_list(test):

    def handle_connect(handler):
        server_timestamp = handler.api.get_info()['server_timestamp']
        test_id = test.generate_id('list-notifications')
        options = [{'notification': '%s-name-1' % test_id,
                    'parameters': {'parameters_key': '1'}},
                   {'notification': '%s-name-2' % test_id,
                    'parameters': {'parameters_key': '2'}}]
        device = handler.api.put_device(test_id)
        for option in options:
            device.send_notification(option['notification'],
                                     parameters=option['parameters'])
        notifications = list_notifications(device)
        assert len(notifications) == len(options)
        notifications = list_notifications(device, start=server_timestamp)
        assert len(notifications) == len(options)
        assert not list_notifications(device, start=server_timestamp,
                                      end=server_timestamp)
        notification_name = options[0]['notification']
        notification, = list_notifications(device,
                                           notification=notification_name)
        assert notification.notification == notification_name
        notification_0, notification_1 = list_notifications(device,
                                                            sort_field=
                                                            'notification',
                                                            sort_order='ASC')
        assert notification_0.notification == options[0]['notification']
        assert notification_1.notification == options[1]['notification']
        notification_0, notification_1 = list_notifications(device,
                                                            sort_field=
                                                            'notification',
                                                            sort_order='DESC')
        assert notification_0.notification == options[1]['notification']
        assert notification_1.notification == options[0]['notification']
        notification_name = test_id
        notification_0 = device.send_notification(notification_name)
        notification_1 = device.send_notification(notification_name)
        notification, = device.list_notifications(notification=
                                                  notification_name,
                                                  sort_field='timestamp',
                                                  sort_order='ASC', take=1)
        assert notification.id == notification_0.id
        notification, = device.list_notifications(notification=
                                                  notification_name,
                                                  sort_field='timestamp',
                                                  sort_order='ASC', take=1,
                                                  skip=1)
        assert notification.id == notification_1.id
        device_1 = handler.api.get_device(test_id)
        device.remove()
        try:
            device.list_notifications()
            assert False
        except DeviceError:
            pass
        try:
            device_1.list_commands()
            assert False
        except ApiResponseError as api_response_error:
            # TODO: uncomment after server response will be fixed.
            # assert api_response_error.code() == 404
            pass

    test.run(handle_connect)


def test_send(test):

    def handle_connect(handler):
        device_id = test.generate_id('send-notification')
        notification_name = test.generate_id('send-notification')
        device = handler.api.put_device(device_id)
        notification = device.send_notification(notification_name)
        assert notification.device_id == device_id
        assert isinstance(notification.id, int)
        assert notification.notification == notification_name
        assert not notification.parameters
        assert notification.timestamp
        parameters = {'parameters_key': 'parameters_value'}
        notification = device.send_notification(notification_name,
                                                parameters=parameters)
        assert notification.device_id == device_id
        assert isinstance(notification.id, int)
        assert notification.notification == notification_name
        assert notification.parameters == parameters
        assert notification.timestamp
        device_1 = handler.api.get_device(device_id)
        device.remove()
        try:
            device.send_notification(notification_name)
            assert False
        except DeviceError:
            pass
        try:
            device_1.send_notification(notification_name)
            assert False
        except ApiResponseError as api_response_error:
            # TODO: uncomment after server response will be fixed.
            # assert api_response_error.code() == 404
            pass

    test.run(handle_connect)
