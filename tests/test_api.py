import pytest
import mock

from odinweb import api


def mock_callback(self, request, **kwargs):
    return 'returned'


class MockResourceApi(object):
    def api_routes(self):
        yield api.ApiRoute(['a', 'b'], ['GET'], mock_callback)
        yield api.ApiRoute(['d', 'e'], ['POST', 'PATCH'], mock_callback)


def flatten_routes(api_routes):
    """
    Remove any iterators for easy comparisons in assert statements.
    """
    def flatten(api_route):
        path, methods, callback = api_route
        return api.ApiRoute(list(path), methods, callback)

    return [flatten(r) for r in api_routes]


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
            api.ApiRoute(['z', 'a', 'b'], ['GET'], mock_callback),
            api.ApiRoute(['z', 'd', 'e'], ['POST', 'PATCH'], mock_callback),
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
            return node.name
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
            api.ApiRoute('/api/a/b', ['GET'], mock_callback),
            api.ApiRoute('/api/d/e', ['POST', 'PATCH'], mock_callback),
        ]),
        ({'url_prefix': 'my-app'}, [
            api.ApiRoute('my-app/api/a/b', ['GET'], mock_callback),
            api.ApiRoute('my-app/api/d/e', ['POST', 'PATCH'], mock_callback),
        ]),
        ({'name': '!api', 'url_prefix': '/my-app'}, [
            api.ApiRoute('/my-app/!api/a/b', ['GET'], mock_callback),
            api.ApiRoute('/my-app/!api/d/e', ['POST', 'PATCH'], mock_callback),
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
    target = MockApiInterface(
        api.ApiVersion(
            MockResourceApi()
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
        api.ApiRoute('/!api/v1/a/b', ['GET'], mock_callback),
        api.ApiRoute('/!api/v1/d/e', ['POST', 'PATCH'], mock_callback),
        api.ApiRoute('/!api/v2/collection/a/b', ['GET'], mock_callback),
        api.ApiRoute('/!api/v2/collection/d/e', ['POST', 'PATCH'], mock_callback),
    ]
