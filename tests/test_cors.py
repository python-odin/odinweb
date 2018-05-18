import pytest

from odinweb import cors
from odinweb.constants import Method
from odinweb.data_structures import HttpResponse
from odinweb.decorators import operation
from odinweb.containers import ApiInterfaceBase
from odinweb.testing import MockRequest


@operation(path='mock-endpoint', methods=(Method.GET, Method.HEAD))
def mock_endpoint(request):
    pass


class TestCORS(object):
    def test_new(self):
        api_interface = ApiInterfaceBase(mock_endpoint)

        actual = cors.CORS(api_interface, cors.AnyOrigin, 20, True, ('X-Custom-A',), ('X-Custom-B',))

        assert actual is api_interface

        target = actual.middleware[0]

        assert isinstance(target, cors.CORS)
        assert target.origins is cors.AnyOrigin
        assert target.max_age == 20
        assert target.allow_credentials is True
        assert target.expose_headers == ('X-Custom-A',)
        assert target.allow_headers == ('X-Custom-B',)

    @pytest.mark.parametrize('cors_config, expected', (
        (dict(origins=cors.AnyOrigin), {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, HEAD',
        }),
        (dict(origins=('http://my-domain.org', 'http://my-alt-domain.org')), {
            'Access-Control-Allow-Origin': 'http://my-domain.org',
            'Access-Control-Allow-Methods': 'GET, HEAD',
        }),
        (dict(origins=('http://my-alt-domain.org',)), {}),
        (dict(origins=cors.AnyOrigin, max_age=20), {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, HEAD',
            'Access-Control-Max-Age': '20',
        }),
        (dict(origins=cors.AnyOrigin, allow_credentials=True), {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, HEAD',
            'Access-Control-Allow-Credentials': 'true',
        }),
        (dict(origins=cors.AnyOrigin, allow_credentials=False), {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, HEAD',
            'Access-Control-Allow-Credentials': 'false',
        }),
        (dict(origins=cors.AnyOrigin, expose_headers=('X-Custom-A', 'X-Custom-C'), allow_headers=('X-Custom-B',)), {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, HEAD',
            'Access-Control-Allow-Headers': 'X-Custom-B',
            'Access-Control-Expose-Headers': 'X-Custom-A, X-Custom-C',
        }),
    ))
    def test_pre_flight_headers(self, cors_config, expected):
        api_interface = ApiInterfaceBase(mock_endpoint)
        cors.CORS(api_interface, **cors_config)
        target = api_interface.middleware[0]
        http_request = MockRequest(headers={'Origin': 'http://my-domain.org'}, current_operation=mock_endpoint)

        actual = target.pre_flight_headers(http_request, mock_endpoint.methods)

        assert 'GET, HEAD' == actual.pop('Allow')
        assert 'no-cache, no-store' == actual.pop('Cache-Control')
        assert expected == actual

    @pytest.mark.parametrize('origins, expected', (
        (cors.AnyOrigin, '*'),
        (('http://my-domain.org',), 'http://my-domain.org'),
        (('http://my-alt-domain.org',), None),
    ))
    def test_cors_options(self, origins, expected):
        api_interface = ApiInterfaceBase(mock_endpoint)
        cors.CORS(api_interface, origins=origins)
        target = api_interface.middleware[0]

        http_request = MockRequest(headers={'Origin': 'http://my-domain.org'}, method=Method.OPTIONS)
        cors._MethodsMiddleware((Method.GET, Method.HEAD)).pre_dispatch(http_request, None)

        actual = target.cors_options(http_request)

        assert isinstance(actual, HttpResponse)
        assert 'GET, HEAD' == actual.headers.pop('Allow')
        assert 'no-cache, no-store' == actual.headers.pop('Cache-Control')
        assert expected == actual.headers.get('Access-Control-Allow-Origin')

    @pytest.mark.parametrize('cors_config, expected', (
        (dict(origins=cors.AnyOrigin), {
            'Access-Control-Allow-Origin': '*',
        }),
        (dict(origins=('http://my-domain.org', 'http://my-alt-domain.org')), {
            'Access-Control-Allow-Origin': 'http://my-domain.org',
        }),
        (dict(origins=('http://my-alt-domain.org',)), {}),
        (dict(origins=cors.AnyOrigin, allow_credentials=True), {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': 'true',
        }),
        (dict(origins=cors.AnyOrigin, allow_credentials=False), {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': 'false',
        }),
        (dict(origins=cors.AnyOrigin, expose_headers=('X-Custom-A', 'X-Custom-C')), {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Expose-Headers': 'X-Custom-A, X-Custom-C',
        }),
    ))
    def test_request_headers(self, cors_config, expected):
        api_interface = ApiInterfaceBase(mock_endpoint)
        cors.CORS(api_interface, **cors_config)
        target = api_interface.middleware[0]
        http_request = MockRequest(headers={'Origin': 'http://my-domain.org'}, current_operation=mock_endpoint)

        actual = target.request_headers(http_request)

        assert expected == actual

    @pytest.mark.parametrize('origins, method, expected', (
        (cors.AnyOrigin, Method.GET, '*'),
        (cors.AnyOrigin, Method.OPTIONS, None),
        (('http://my-domain.org',), Method.GET, 'http://my-domain.org'),
        (('http://my-domain.org',), Method.OPTIONS, None),
        (('http://my-alt-domain.org',), Method.GET, None),
    ))
    def test_post_request(self, origins, method, expected):
        api_interface = ApiInterfaceBase(mock_endpoint)
        cors.CORS(api_interface, origins=origins)
        target = api_interface.middleware[0]

        http_request = MockRequest(headers={'Origin': 'http://my-domain.org'}, method=method, current_operation=mock_endpoint)
        http_response = HttpResponse('')

        actual = target.post_request(http_request, http_response)

        assert actual is http_response
        assert expected == actual.headers.get('Access-Control-Allow-Origin')
