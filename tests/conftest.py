import six
import logging.config
from tests.test import Test


USER_ROLES = ['admin', 'client']


def pytest_addoption(parser):
    parser.addoption('--transport-urls', action='store',
                     help='Comma separated transport urls')

    for role in USER_ROLES:
        parser.addoption('--%s-refresh-token' % role, action='store',
                         help='%s refresh token' % role.capitalize())
        parser.addoption('--%s-access-token' % role, action='store',
                         help='%s access token' % role.capitalize())
        parser.addoption('--%s-login' % role, action='store',
                         help='%s login' % role.capitalize())
        parser.addoption('--%s-password' % role, action='store',
                         help='%s password' % role.capitalize())


def pytest_generate_tests(metafunc):
    if metafunc.module.__name__.find('.test_api') == -1:
        return
    options = metafunc.config.option
    transport_urls = options.transport_urls.split(',')
    role_credentials = {}
    for role in USER_ROLES:
        refresh_token = getattr(options, '%s_refresh_token' % role, None)
        access_token = getattr(options, '%s_access_token' % role, None)
        login = getattr(options, '%s_login' % role, None)
        password = getattr(options, '%s_password' % role, None)

        if refresh_token:
            role_credentials[role] = {'refresh_token': refresh_token}
        elif access_token:
            role_credentials[role] = {'access_token': access_token}
        elif login and password:
            role_credentials[role] = {'login': login, 'password': password}

    log_level = options.log_level or 'INFO'

    logger = logging.getLogger('devicehive')
    logger.setLevel(log_level)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s] %(message)s',
                                  '%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    tests = []
    ids = []
    for transport_url in transport_urls:
        for user_role, credentials in six.iteritems(role_credentials):
            tests.append(Test(transport_url, user_role, credentials))
            ids.append('%s:%s' % (user_role, transport_url))
    metafunc.parametrize('test', tests, ids=ids)


def pytest_exception_interact(node, call, report):
    if not hasattr(node, 'funcargs'):
        return

    test = node.funcargs['test']
    api = test.device_hive_api()
    for entity_type, entity_ids in six.iteritems(test.entity_ids):
        if entity_type is None:
            continue
        for entity_id in entity_ids:
            try:
                getattr(api, 'get_%s' % entity_type)(entity_id).remove()
                print('Remove %s "%s"' % (entity_type, entity_id))
            except:
                pass
