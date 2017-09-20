from tests.test import Test


def pytest_addoption(parser):
    parser.addoption('--transport-urls', action='store', help='Transport urls')
    parser.addoption('--admin-refresh-token', action='store',
                     help='Admin refresh tokens')
    parser.addoption('--user-refresh-token', action='store',
                     help='User refresh tokens')


def pytest_generate_tests(metafunc):
    if metafunc.module.__name__.find('.test_api') == -1:
        return
    transport_urls = metafunc.config.option.transport_urls.split(',')
    refresh_tokens = {'admin': metafunc.config.option.admin_refresh_token,
                      'user': metafunc.config.option.user_refresh_token}
    tests = []
    ids = []
    for transport_url in transport_urls:
        for token_type, refresh_token in refresh_tokens.items():
            if not refresh_token:
                continue
            tests.append(Test(transport_url, refresh_token, token_type))
            ids.append('%s:%s' % (token_type, transport_url))
    metafunc.parametrize('test', tests, ids=ids)
