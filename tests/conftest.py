def pytest_addoption(parser):
    parser.addoption('--transport-urls', action='store', help="Transport urls")
    parser.addoption('--refresh-token', action='store', help="Refresh token")


def pytest_generate_tests(metafunc):
    transport_urls = metafunc.config.option.transport_urls.split(',')
    refresh_token = metafunc.config.option.refresh_token
    run_options = [{'transport_url': transport_url,
                    'refresh_token': refresh_token}
                   for transport_url in transport_urls]
    metafunc.parametrize('run_options', run_options)
