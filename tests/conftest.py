from tests.test import Test


def pytest_addoption(parser):
    parser.addoption('--transport-urls', action='store', help="Transport urls")
    parser.addoption('--refresh-token', action='store', help="Refresh token")


def pytest_generate_tests(metafunc):
    transport_urls = metafunc.config.option.transport_urls.split(',')
    refresh_token = metafunc.config.option.refresh_token
    tests = []
    ids = []
    for transport_url in transport_urls:
        tests.append(Test(transport_url, refresh_token))
        ids.append(transport_url)
    metafunc.parametrize('test', tests, ids=ids)
