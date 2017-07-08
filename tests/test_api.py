from __future__ import absolute_import

import pytest
import mock

from odin.exceptions import ValidationError
from odinweb import api, decorators
from .resources import User


def flatten_routes(api_routes):
    """
    Remove any iterators for easy comparisons in assert statements.
    """
    def flatten(api_route):
        path, methods, callback = api_route
        return api.ApiRoute(
            ["<%s>" % p.name if isinstance(p, api.PathNode) else p for p in path],
            methods, callback
        )

    return [flatten(r) for r in api_routes]


class TestResourceApiMeta(object):
    def test_empty_api(self, mocker):
        mocker.patch('odinweb.decorators._route_count', 0)

        class ExampleApi(api.ResourceApi):
            pass

        assert ExampleApi._routes == []

    def test_normal_api(self, mocker):
        mocker.patch('odinweb.decorators._route_count', 0)

        class ExampleApi(api.ResourceApi):
            @api.collection
            def list_items(self, request):
                pass

            @api.detail
            def get_item(self, request, resource_id):
                pass

            @api.route(methods=('POST', 'PUT'))
            def create_item(self, request):
                pass

        assert ExampleApi._routes == [
            decorators.RouteDefinition(0, 'collection', ('GET',), None, ExampleApi.__dict__['list_items']),
            decorators.RouteDefinition(1, 'resource', ('GET',), None, ExampleApi.__dict__['get_item']),
            decorators.RouteDefinition(2, 'collection', ('POST', 'PUT'), None, ExampleApi.__dict__['create_item']),
        ]

    def test_sub_classed_api(self, mocker):
        mocker.patch('odinweb.decorators._route_count', 0)

        class SuperApi(api.ResourceApi):
            @api.collection
            def list_items(self, request):
                pass

        class SubApi(SuperApi):
            @api.detail
            def get_item(self, request, resource_id):
                pass

            @api.route(methods=('POST', 'PUT'))
            def create_item(self, request):
                pass

        assert SubApi._routes == [
            decorators.RouteDefinition(0, 'collection', ('GET',), None, SuperApi.__dict__['list_items']),
            decorators.RouteDefinition(1, 'resource', ('GET',), None, SubApi.__dict__['get_item']),
            decorators.RouteDefinition(2, 'collection', ('POST', 'PUT'), None, SubApi.__dict__['create_item']),
        ]


class UserApi(api.ResourceApi):
    resource = User

    @api.collection
    def list_items(self, request):
        return [User(1, 'Dave'), User(2, 'Bob')]

    @api.detail
    def get_item(self, request, resource_id):
        return User(resource_id, 'Dave')

    @api.detail_action(sub_path='start', method=api.POST)
    def start_item(self, request):
        return self.create_response(request, status=202)


class MockRequest(object):
    def __init__(self, method='GET', headers=None):
        self.method = method
        self.headers = headers or {}


class TestResourceApi(object):
    def test_api_name__default(self):
        target = UserApi()

        assert target.api_name == 'user'

    def test_api_name__custom(self):
        class Example(api.ResourceApi):
            resource = User
            api_name = 'users'

        target = Example()

        assert target.api_name == 'users'

    def test_debug_enabled__no_parent(self):
        target = UserApi()

        assert not target.debug_enabled

    def test_debug_enabled__with_parent(self):
        parent = mock.Mock()
        parent.debug_enabled = True

        target = UserApi()
        target.parent = parent

        assert target.debug_enabled

    def test_api_routes(self):
        target = UserApi()
        target._wrap_callback = lambda callback, methods: callback

        actual = flatten_routes(target.api_routes())

        assert actual == [
            api.ApiRoute(['user'], ('GET',), UserApi.__dict__['list_items']),
            api.ApiRoute(['user', '<resource_id>'], ('GET',), UserApi.__dict__['get_item']),
            api.ApiRoute(['user', '<resource_id>', 'start'], ('POST',), UserApi.__dict__['start_item']),
        ]

    @pytest.mark.parametrize('r, status, message', (
        (MockRequest(headers={'content-type': 'application/xml', 'accepts': 'application/json'}),
         406, 'Un-supported body content.'),
        (MockRequest(headers={'content-type': 'application/json', 'accepts': 'application/xml'}),
         406, 'Un-supported response type.'),
        (MockRequest('POST'), 405, 'Method not allowed.'),
    ))
    def test_wrap_callback__invalid_headers(self, r, status, message):
        def callback(s, request):
            pass

        target = UserApi()
        wrapper = target._wrap_callback(callback, ['GET'])
        actual = wrapper(r)

        assert actual.body == message
        assert actual.status == status

    @pytest.mark.parametrize('error,status', (
        (api.ImmediateHttpResponse(None, 330, {}), 330),
        (ValidationError("Error"), 400),
        (ValidationError({}), 400),
        (NotImplementedError, 501),
        (ValueError, 500)
    ))
    def test_wrap_callback__exceptions(self, error, status):
        def callback(s, request):
            raise error

        target = UserApi()
        wrapper = target._wrap_callback(callback, ['GET'])
        actual = wrapper(MockRequest())

        assert actual.status == status




def mock_callback(self, request, **kwargs):
    return 'returned'


class MockResourceApi(object):
    def api_routes(self):
        yield api.ApiRoute(['a', 'b'], ('GET',), mock_callback)
        yield api.ApiRoute(['d', 'e'], ('POST', 'PATCH'), mock_callback)


class TestApiContainer(object):
    @pytest.mark.parametrize('options,attr,value', (
        ({}, 'name', None),
        ({'name': 'foo'}, 'name', 'foo'),
        ({}, 'path_prefix', []),
        ({'name': 'foo'}, 'path_prefix', ['foo']),
        ({'path_prefix': ['bar']}, 'path_prefix', ['bar']),
    ))
    def test_options(self, options, attr, value):
        target = api.ApiContainer(**options)

        assert hasattr(target, attr)
        assert getattr(target, attr) == value

    def test_extra_option(self):
        with pytest.raises(TypeError, message="Got an unexpected keyword argument 'foo'"):
            api.ApiContainer(foo=1, name='test')

        with pytest.raises(TypeError):
            api.ApiContainer(foo=1, bar=2)

    def test_api_routes(self):
        target = api.ApiContainer(MockResourceApi(), path_prefix=['z'])

        actual = flatten_routes(target.api_routes())
        assert actual == [
            api.ApiRoute(['z', 'a', 'b'], ('GET',), mock_callback),
            api.ApiRoute(['z', 'd', 'e'], ('POST', 'PATCH'), mock_callback),
        ]

    def test_additional_routes(self):
        target = api.ApiContainer(path_prefix=['z'])
        target.additional_routes = [
            api.ApiRoute(['f'], ['GET'], None)
        ]

        actual = flatten_routes(target.api_routes())
        assert actual == [
            api.ApiRoute(['z', 'f'], ['GET'], None),
        ]

    def test_callable_additional_routes(self):
        target = api.ApiContainer(path_prefix=['z'])
        target.additional_routes = lambda: [
            api.ApiRoute(['f'], ['GET'], None)
        ]

        actual = flatten_routes(target.api_routes())
        assert actual == [
            api.ApiRoute(['z', 'f'], ['GET'], None),
        ]


class TestApiCollection(object):
    """
    Actually test with ApiVersion is this is a thin layer over a collection.
    """
    def test_debug_enabled__no_parent(self):
        target = api.ApiVersion()

        assert not target.debug_enabled

    def test_debug_enabled__with_parent(self):
        parent = mock.Mock()
        parent.debug_enabled = True

        target = api.ApiVersion()
        target.parent = parent

        assert target.debug_enabled

    @pytest.mark.parametrize('options,version,name,path_prefix', (
        ({}, 1, 'v1', ['v1']),
        ({'version': 2}, 2, 'v2', ['v2']),
        ({'version': 3, 'name': 'version-3'}, 3, 'version-3', ['version-3']),
    ))
    def test_version_options(self, options, version, name, path_prefix):
        target = api.ApiVersion(**options)

        assert target.version == version
        assert target.name == name
        assert target.path_prefix == path_prefix


class MockApiInterface(api.ApiInterfaceBase):
    def parse_node(self, node):
        if isinstance(node, api.PathNode):
            return "<%s>" % node.name
        else:
            return str(node)


class TestApiInterfaceBase(object):
    @pytest.mark.parametrize('options,name,url_prefix,debug_enabled,path_prefix', (
        ({}, 'api', '/', False, ['api']),
        ({'name': '!api'}, '!api', '/', False, ['!api']),
        ({'url_prefix': '/my-app/'}, 'api', '/my-app/', False, ['api']),
        ({'debug_enabled': True}, 'api', '/', True, ['api']),
    ))
    def test_options(self, options, name, url_prefix, debug_enabled, path_prefix):
        target = api.ApiInterfaceBase(**options)

        assert target.name == name
        assert target.url_prefix == url_prefix
        assert target.debug_enabled == debug_enabled
        assert target.path_prefix == path_prefix

    @pytest.mark.parametrize('options,api_routes', (
        ({}, [
            api.ApiRoute('/api/a/b', ('GET',), mock_callback),
            api.ApiRoute('/api/d/e', ('POST', 'PATCH'), mock_callback),
        ]),
        ({'url_prefix': 'my-app'}, [
            api.ApiRoute('my-app/api/a/b', ('GET',), mock_callback),
            api.ApiRoute('my-app/api/d/e', ('POST', 'PATCH'), mock_callback),
        ]),
        ({'name': '!api', 'url_prefix': '/my-app'}, [
            api.ApiRoute('/my-app/!api/a/b', ('GET',), mock_callback),
            api.ApiRoute('/my-app/!api/d/e', ('POST', 'PATCH'), mock_callback),
        ]),
    ))
    def test_build_routes(self, options, api_routes):
        target = MockApiInterface(MockResourceApi(), **options)

        actual = list(target.build_routes())
        assert actual == api_routes

    def test_ensure_parse_node_is_implemented(self):
        target = api.ApiInterfaceBase()

        with pytest.raises(NotImplementedError):
            target.parse_node(None)


def test_nested_api():
    user_api = UserApi()
    user_api._wrap_callback = lambda callback, methods: callback

    target = MockApiInterface(
        api.ApiVersion(
            user_api
        ),
        api.ApiVersion(
            api.ApiCollection(
                MockResourceApi(),
                name='collection'
            ),
            version=2
        ),
        name='!api'
    )

    actual = list(target.build_routes())
    assert actual == [
        api.ApiRoute('/!api/v1/user', ('GET',), UserApi.__dict__['list_items']),
        api.ApiRoute('/!api/v1/user/<resource_id>', ('GET',), UserApi.__dict__['get_item']),
        api.ApiRoute('/!api/v1/user/<resource_id>/start', ('POST',), UserApi.__dict__['start_item']),
        api.ApiRoute('/!api/v2/collection/a/b', ('GET',), mock_callback),
        api.ApiRoute('/!api/v2/collection/d/e', ('POST', 'PATCH'), mock_callback),
    ]
