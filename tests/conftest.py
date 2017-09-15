from tests.test import Test


def pytest_addoption(parser):
    parser.addoption('--transport-urls', action='store', help='Transport urls')
    parser.addoption('--refresh-token', action='store', help='Refresh tokens')


def pytest_generate_tests(metafunc):
    if metafunc.module.__name__.find('.test_api') == -1:
        return
    transport_urls = metafunc.config.option.transport_urls.split(',')
    refresh_tokens = metafunc.config.option.refresh_token.split(',')
    refresh_tokens = map(lambda t: t.split(':'), refresh_tokens)
    tests = []
    ids = []
    for transport_url in transport_urls:
        for token_type, refresh_token in refresh_tokens:
            tests.append(Test(transport_url, refresh_token, token_type))
            ids.append(transport_url)
    metafunc.parametrize('test', tests, ids=ids)
