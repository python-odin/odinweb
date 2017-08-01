from __future__ import absolute_import

import mock
import pytest

from odinweb import api
from odinweb import containers
from odinweb.constants import Method
from odinweb.data_structures import NoPath, UrlPath, PathNode
from odinweb.decorators import Operation
from odinweb.helpers import create_response

from .resources import User


#################################################
# Mocks

def mock_callback(self, request, **kwargs):
    return 'returned'


class UserApi(containers.ResourceApi):
    resource = User

    def __init__(self):
        super(UserApi, self).__init__()
        self.calls = []

    @api.collection
    def list_items(self, request):
        self.calls.append('list_items')
        return [User(1, 'Dave'), User(2, 'Bob')]

    @api.detail
    def get_item(self, request, resource_id):
        self.calls.append('get_item')
        return User(resource_id, 'Dave')

    @api.action(url_path='start', methods=Method.POST)
    def start_item(self, request):
        self.calls.append('start_item')
        return create_response(request, status=202)

    def mock_callback(self, request, **path_args):
        self.calls.append('mock_callback')
        return path_args


class MockResourceApi(object):
    def op_paths(self, path_base):
        yield path_base + UrlPath.parse('a/b'), Operation(mock_callback, UrlPath.parse('a/b'), Method.GET)
        yield path_base + UrlPath.parse('d/e'), Operation(mock_callback, UrlPath.parse('d/e'), (Method.POST, Method.PATCH))


class MockApiInterface(containers.ApiInterfaceBase):
    pass


################################################
# Tests

class TestResourceApiMeta(object):
    def test_empty_api(self, mocker):
        mocker.patch('odinweb.decorators.Operation._operation_count', 0)

        class ExampleApi(api.ResourceApi):
            pass

        assert ExampleApi._operations == []

    def test_normal_api(self, mocker):
        mocker.patch('odinweb.decorators.Operation._operation_count', 0)

        class ExampleApi(api.ResourceApi):
            @api.collection
            def list_items(self, request):
                pass

            @api.detail
            def get_item(self, request, resource_id):
                pass

            @api.Operation(methods=(Method.POST, Method.PUT))
            def create_item(self, request):
                pass

        assert ExampleApi._operations == [
            Operation(mock_callback, NoPath, Method.GET),
            Operation(mock_callback, UrlPath(PathNode('resource_id')), Method.GET),
            Operation(mock_callback, NoPath, (Method.POST, Method.PUT)),
        ]

    def test_sub_classed_api(self, mocker):
        mocker.patch('odinweb.decorators.Operation._operation_count', 0)

        class SuperApi(api.ResourceApi):
            @api.collection
            def list_items(self, request):
                pass

        class SubApi(SuperApi):
            @api.detail
            def get_item(self, request, resource_id):
                pass

            @Operation(methods=(Method.POST, Method.PUT))
            def create_item(self, request):
                pass

        assert SubApi._operations == [
            Operation(mock_callback, NoPath, Method.GET),
            Operation(mock_callback, UrlPath(PathNode('resource_id')), Method.GET),
            Operation(mock_callback, NoPath, (Method.POST, Method.PUT)),
        ]


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

    def test_op_paths(self):
        target = UserApi()

        actual = dict(target.op_paths(NoPath))

        assert actual == {
            UrlPath.parse('user'): Operation(mock_callback, NoPath, methods=Method.GET),
            UrlPath('user', PathNode('resource_id')): Operation(mock_callback, UrlPath(PathNode('resource_id')), methods=Method.GET),
            UrlPath.parse('user/start'): Operation(mock_callback, UrlPath.parse('start'), methods=Method.POST),
        }


class TestApiContainer(object):
    @pytest.mark.parametrize('options,attr,value', (
        ({}, 'name', None),
        ({'name': 'foo'}, 'name', 'foo'),
        ({}, 'path_prefix', UrlPath()),
        ({'name': 'foo'}, 'path_prefix', UrlPath('foo')),
        ({'path_prefix': ['bar']}, 'path_prefix', UrlPath('bar')),
    ))
    def test_options(self, options, attr, value):
        target = containers.ApiContainer(**options)

        assert hasattr(target, attr)
        assert getattr(target, attr) == value

    def test_extra_option(self):
        with pytest.raises(TypeError, message="Got an unexpected keyword argument 'foo'"):
            containers.ApiContainer(foo=1, name='test')

        with pytest.raises(TypeError):
            containers.ApiContainer(foo=1, bar=2)

    def test_op_paths(self):
        target = containers.ApiContainer(MockResourceApi())

        actual = dict(target.op_paths('c'))

        assert actual == {
            UrlPath.parse('c/a/b'): Operation(mock_callback, 'a/b', Method.GET),
            UrlPath.parse('c/d/e'): Operation(mock_callback, 'd/e', (Method.POST, Method.PATCH)),
        }

    def test_op_paths__no_sub_path(self):
        target = containers.ApiContainer(MockResourceApi())

        actual = dict(target.op_paths())

        assert actual == {
            UrlPath.parse('a/b'): Operation(mock_callback, 'a/b', Method.GET),
            UrlPath.parse('d/e'): Operation(mock_callback, 'd/e', (Method.POST, Method.PATCH)),
        }


class TestApiCollection(object):
    """
    Actually test with ApiVersion is this is a thin layer over a collection.
    """
    @pytest.mark.parametrize('options,version,name,path_prefix', (
        ({}, 1, 'v1', UrlPath('v1')),
        ({'version': 2}, 2, 'v2', UrlPath('v2')),
        ({'version': 3, 'name': 'version-3'}, 3, 'version-3', UrlPath('version-3')),
    ))
    def test_version_options(self, options, version, name, path_prefix):
        target = containers.ApiVersion(**options)

        assert target.version == version
        assert target.name == name
        assert target.path_prefix == path_prefix

    def test_register_operation(self):
        target = containers.ApiCollection()

        @target.operation(url_path="a/b")
        def my_operation(request):
            pass

        actual = dict(target.op_paths())

        assert len(actual) == 1
        assert actual == {
            UrlPath.parse("a/b"): Operation(mock_callback, 'a/b')
        }


class TestApiInterfaceBase(object):
    @pytest.mark.parametrize('options,name,debug_enabled,path_prefix', (
        ({}, 'api', False, UrlPath.parse('/api')),
        ({'name': '!api'}, '!api', False, UrlPath.parse('/!api')),
        ({'path_prefix': '/my-app/'}, 'api', False, UrlPath.parse('/my-app')),
        ({'debug_enabled': True}, 'api', True, UrlPath.parse('/api')),
    ))
    def test_options(self, options, name, debug_enabled, path_prefix):
        target = containers.ApiInterfaceBase(**options)

        assert target.name == name
        assert target.debug_enabled == debug_enabled
        assert target.path_prefix == path_prefix

    def test_init_non_absolute(self):
        with pytest.raises(ValueError):
            containers.ApiInterfaceBase(path_prefix='ab/c')

# #     @pytest.mark.parametrize('r, status, message', (
# #         (MockRequest(headers={'content-type': 'application/xml', 'accepts': 'application/json'}),
# #          422, 'Unprocessable Entity'),
# #         (MockRequest(headers={'content-type': 'application/json', 'accepts': 'application/xml'}),
# #          406, 'URI not available in preferred format'),
# #         (MockRequest('POST'), 405, 'Specified method is invalid for this resource'),
# #     ))
# #     def test_wrap_callback__invalid_headers(self, r, status, message):
# #         def callback(s, request):
# #             pass
# #
# #         target = UserApi()
# #         wrapper = target._wrap_callback(callback, ['GET'])
# #         actual = wrapper(r)
# #
# #         assert actual.status == status
# #         assert actual.body == message
# #
# #     @pytest.mark.parametrize('error,status', (
# #         (api.ImmediateHttpResponse(None, 330, {}), 330),
# #         (ValidationError("Error"), 400),
# #         (ValidationError({}), 400),
# #         (NotImplementedError, 501),
# #         (ValueError, 500)
# #     ))
# #     def test_wrap_callback__exceptions(self, error, status):
# #         def callback(s, request):
# #             raise error
# #
# #         target = UserApi()
# #         wrapper = target._wrap_callback(callback, ['GET'])
# #         actual = wrapper(MockRequest())
# #
# #         assert actual.status == status
# #
# #     def test_dispatch__with_authorisation(self):
# #         class AuthorisedUserApi(UserApi):
# #             def handle_authorisation(self, request):
# #                 self.calls.append('handle_authorisation')
# #
# #         target = AuthorisedUserApi()
# #         result = target.dispatch(UserApi.mock_callback, MockRequest(), a="b")
# #
# #         assert 'handle_authorisation' in target.calls
# #         assert result == {"a": "b"}
# #
# #     def test_dispatch__with_pre_dispatch(self):
# #         class AuthorisedUserApi(UserApi):
# #             def pre_dispatch(self, request, **path_args):
# #                 self.calls.append('pre_dispatch')
# #
# #         target = AuthorisedUserApi()
# #         result = target.dispatch(UserApi.mock_callback, MockRequest(), a="b")
# #
# #         assert 'pre_dispatch' in target.calls
# #         assert 'mock_callback' in target.calls
# #         assert result == {"a": "b"}
# #
# #     def test_dispatch__with_pre_dispatch_modify_path_args(self):
# #         class AuthorisedUserApi(UserApi):
# #             def pre_dispatch(self, request, **path_args):
# #                 self.calls.append('pre_dispatch')
# #                 return {}
# #
# #         target = AuthorisedUserApi()
# #         result = target.dispatch(UserApi.mock_callback, MockRequest(), a="b")
# #
# #         assert 'pre_dispatch' in target.calls
# #         assert 'mock_callback' in target.calls
# #         assert result == {}
# #
# #     def test_dispatch__with_post_dispatch(self):
# #         class AuthorisedUserApi(UserApi):
# #             def post_dispatch(self, request, result):
# #                 self.calls.append('post_dispatch')
# #                 result['c'] = 'd'
# #                 return result
# #
# #         target = AuthorisedUserApi()
# #         result = target.dispatch(UserApi.mock_callback, MockRequest(), a="b")
# #
# #         assert 'post_dispatch' in target.calls
# #         assert 'mock_callback' in target.calls
# #         assert result == {"a": "b", "c": "d"}
# #
# #
# #     @pytest.mark.parametrize('value, body, status', (
# #         (None, None, 204),
# #         ('abc', '"abc"', 200),
# #         (123, '123', 200),
# #         ([], None, 204),
# #         ([1, 2, 3], '[1, 2, 3]', 200),
# #         (set("123"), 'Error encoding response.', 500),
# #     ))
# #     def test_create_response(self, value, body, status):
# #         target = UserApi()
# #         request = MockRequest()
# #
# #         actual = target.create_response(request, value)
# #         assert actual.body == body
# #         assert actual.status == status

# # def test_nested_api():
# #     user_api = UserApi()
# #     user_api._wrap_callback = lambda callback, methods: callback
# #
# #     target = MockApiInterface(
# #         api.ApiVersion(
# #             user_api
# #         ),
# #         api.ApiVersion(
# #             api.ApiCollection(
# #                 MockResourceApi(),
# #                 name='collection'
# #             ),
# #             version=2
# #         ),
# #         name='!api'
# #     )
# #
# #     actual = list(target.build_routes())
# #     assert actual == [
# #         api.ApiRoute('/!api/v1/user', ('GET',), UserApi.__dict__['list_items']),
# #         api.ApiRoute('/!api/v1/user/<resource_id>', ('GET',), UserApi.__dict__['get_item']),
# #         api.ApiRoute('/!api/v1/user/<resource_id>/start', ('POST',), UserApi.__dict__['start_item']),
# #         api.ApiRoute('/!api/v2/collection/a/b', ('GET',), mock_callback),
# #         api.ApiRoute('/!api/v2/collection/d/e', ('POST', 'PATCH'), mock_callback),
# #     ]
