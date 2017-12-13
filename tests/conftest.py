import six
import logging.config
from tests.test import Test


def pytest_addoption(parser):
    parser.addoption('--transport-urls', action='store',
                     help='Comma separated transport urls')
    parser.addoption('--admin-refresh-token', action='store',
                     help='Admin refresh token')
    parser.addoption('--user-refresh-token', action='store',
                     help='User refresh token')


def pytest_generate_tests(metafunc):
    if metafunc.module.__name__.find('.test_api') == -1:
        return
    transport_urls = metafunc.config.option.transport_urls.split(',')
    refresh_tokens = {'admin': metafunc.config.option.admin_refresh_token,
                      'user': metafunc.config.option.user_refresh_token}
    log_level = metafunc.config.option.log_level or 'INFO'

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
        for token_type, refresh_token in refresh_tokens.items():
            if not refresh_token:
                continue
            tests.append(Test(transport_url, refresh_token, token_type))
            ids.append('%s:%s' % (token_type, transport_url))
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
                print('Remove {} "{}"'.format(entity_type, entity_id))
            except:
                pass
