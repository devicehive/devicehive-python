from tests.test import Test
import logging.config


def pytest_addoption(parser):
    parser.addoption('--transport-urls', action='store',
                     help='Comma separated transport urls')
    parser.addoption('--admin-refresh-token', action='store',
                     help='Admin refresh token')
    parser.addoption('--user-refresh-token', action='store',
                     help='User refresh token')
    parser.addoption('--log-level', action='store', default='INFO',
                     help='Log level')


def pytest_generate_tests(metafunc):
    if metafunc.module.__name__.find('.test_api') == -1:
        return
    transport_urls = metafunc.config.option.transport_urls.split(',')
    refresh_tokens = {'admin': metafunc.config.option.admin_refresh_token,
                      'user': metafunc.config.option.user_refresh_token}
    log_level = metafunc.config.option.log_level
    handlers = {'console': {'level': log_level,
                            'formatter': 'console',
                            'class': 'logging.StreamHandler'}}
    formatters = {'console': {'format': '%(asctime)s %(message)s',
                              'datefmt': '%Y-%m-%d %H:%M:%S'}}
    loggers = {'devicehive.api_request': {'handlers': ['console'],
                                          'level': log_level,
                                          'propagate': False}}
    logging.config.dictConfig({'version': 1,
                               'handlers': handlers,
                               'formatters': formatters,
                               'loggers': loggers})
    tests = []
    ids = []
    for transport_url in transport_urls:
        for token_type, refresh_token in refresh_tokens.items():
            if not refresh_token:
                continue
            tests.append(Test(transport_url, refresh_token, token_type))
            ids.append('%s:%s' % (token_type, transport_url))
    metafunc.parametrize('test', tests, ids=ids)
