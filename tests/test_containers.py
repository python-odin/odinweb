from __future__ import absolute_import

import pytest
from odinweb.resources import Error

from odin.exceptions import ValidationError
from odinweb import api
from odinweb import containers
from odinweb.constants import Method, HTTPStatus
from odinweb.data_structures import NoPath, UrlPath, HttpResponse
from odinweb.decorators import Operation
from odinweb.helpers import create_response
from odinweb.testing import MockRequest

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

    @api.action(path='start', methods=Method.POST)
    def start_item(self, request):
        self.calls.append('start_item')
        return create_response(request, status=202)

    def mock_callback(self, request, **path_args):
        self.calls.append('mock_callback')
        return path_args


class MockResourceApi(object):
    def op_paths(self, path_base):
        yield path_base + UrlPath.parse('a/b'), Operation(mock_callback, UrlPath.parse('a/b'), Method.GET)
        yield path_base + UrlPath.parse('a/b'), Operation(mock_callback, UrlPath.parse('a/b'), Method.POST)
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
            Operation(mock_callback, '{resource_id}', Method.GET),
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
            Operation(mock_callback, '{resource_id}', Method.GET),
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
            UrlPath.parse('user/{resource_id}'): Operation(mock_callback, '{resource_id}', methods=Method.GET),
            UrlPath.parse('user/start'): Operation(mock_callback, 'start', methods=Method.POST),
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
            UrlPath.parse('c/a/b'): Operation(mock_callback, 'a/b', Method.POST),
            UrlPath.parse('c/d/e'): Operation(mock_callback, 'd/e', (Method.POST, Method.PATCH)),
        }

    def test_op_paths__no_sub_path(self):
        target = containers.ApiContainer(MockResourceApi())

        actual = dict(target.op_paths())

        assert actual == {
            UrlPath.parse('a/b'): Operation(mock_callback, 'a/b', Method.GET),
            UrlPath.parse('a/b'): Operation(mock_callback, 'a/b', Method.POST),
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

        @target.operation("a/b")
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

    def test_dispatch(self):
        pass

    @pytest.mark.parametrize('r, status, message', (
        (MockRequest(headers={'content-type': 'application/xml', 'accepts': 'application/json'}),
         422, 'Unprocessable Entity'),
        (MockRequest(headers={'content-type': 'application/json', 'accepts': 'application/xml'}),
         406, 'URI not available in preferred format'),
        (MockRequest(method=Method.POST), 405, 'Specified method is invalid for this resource'),
    ))
    def test_dispatch__invalid_headers(self, r, status, message):
        target = containers.ApiInterfaceBase()
        operation = Operation(mock_callback)
        actual = target.dispatch(operation, r)

        assert actual.status == status
        assert actual.body == message

    @pytest.mark.parametrize('error,status', (
        (api.ImmediateHttpResponse(None, HTTPStatus.NOT_MODIFIED, {}), HTTPStatus.NOT_MODIFIED),
        (ValidationError("Error"), 400),
        (ValidationError({}), 400),
        (NotImplementedError, 501),
        (ValueError, 500),
        (api.ImmediateHttpResponse(ValueError, HTTPStatus.NOT_MODIFIED, {}), 500),
    ))
    def test_dispatch__exceptions(self, error, status):
        def callback(request):
            raise error

        target = containers.ApiInterfaceBase()
        operation = Operation(callback)
        actual = target.dispatch(operation, MockRequest())

        assert actual.status == status

    def test_dispatch__with_middleware(self):
        calls = []

        class Middleware(object):
            def pre_request(self, request, path_args):
                calls.append('pre_request')

            def pre_dispatch(self, request, path_args):
                calls.append('pre_dispatch')
                path_args['foo'] = 'bar'

            def post_dispatch(self, request, response):
                calls.append('post_dispatch')
                return 'eek' + response

            def post_request(self, request, response):
                calls.append('post_request')
                response['test'] = 'header'
                return response

        def callback(request, **args):
            assert args['foo'] == 'bar'
            return 'boo'

        target = containers.ApiInterfaceBase(middleware=[Middleware()])
        operation = Operation(callback)
        actual = target.dispatch(operation, MockRequest())

        assert actual.body == '"eekboo"'
        assert actual.status == 200
        assert 'test' in actual.headers
        assert calls == ['pre_request', 'pre_dispatch', 'post_dispatch', 'post_request']

    def test_dispatch__error_with_debug_enabled(self):
        def callback(request):
            raise ValueError()

        target = containers.ApiInterfaceBase(debug_enabled=True)
        operation = Operation(callback)

        with pytest.raises(ValueError):
            target.dispatch(operation, MockRequest())

    def test_dispatch__error_handled_by_middleware(self):
        class ErrorMiddleware(object):
            def handle_500(self, request, exception):
                assert isinstance(exception, ValueError)
                return Error.from_status(HTTPStatus.SEE_OTHER, 0,
                                         "Quick over there...")

        def callback(request):
            raise ValueError()

        target = containers.ApiInterfaceBase(middleware=[ErrorMiddleware()])
        operation = Operation(callback)

        actual = target.dispatch(operation, MockRequest())
        assert actual.status == 303

    def test_dispatch__error_handled_by_middleware_raises_exception(self):
        class ErrorMiddleware(object):
            def handle_500(self, request, exception):
                assert isinstance(exception, ValueError)
                raise ValueError

        def callback(request):
            raise ValueError()

        target = containers.ApiInterfaceBase(middleware=[ErrorMiddleware()])
        operation = Operation(callback)

        actual = target.dispatch(operation, MockRequest())
        assert actual.status == 500

    def test_dispatch__encode_error_with_debug_enabled(self):
        def callback(request):
            raise api.ImmediateHttpResponse(ValueError, HTTPStatus.NOT_MODIFIED, {})

        target = containers.ApiInterfaceBase(debug_enabled=True)
        operation = Operation(callback)

        with pytest.raises(TypeError):
            target.dispatch(operation, MockRequest())

    def test_dispatch__http_response(self):
        def callback(request):
            return HttpResponse("eek")

        target = containers.ApiInterfaceBase()
        operation = Operation(callback)
        actual = target.dispatch(operation, MockRequest())

        assert actual.body == 'eek'
        assert actual.status == 200

    def test_op_paths(self):
        target = containers.ApiInterfaceBase(MockResourceApi())

        actual = list(target.op_paths())

        assert actual == [
            (UrlPath.parse('/api/a/b'), Operation(mock_callback, 'a/b', Method.GET)),
            (UrlPath.parse('/api/a/b'), Operation(mock_callback, 'a/b', Method.POST)),
            (UrlPath.parse('/api/d/e'), Operation(mock_callback, 'd/e', (Method.POST, Method.PATCH))),
        ]

    def test_op_paths__collate_methods(self):
        target = containers.ApiInterfaceBase(MockResourceApi())

        actual = target.op_paths(collate_methods=True)

        assert actual == {
            UrlPath.parse('/api/a/b'): {
                Method.GET: Operation(mock_callback, 'a/b', Method.GET),
                Method.POST: Operation(mock_callback, 'a/b', Method.POST),
            },
            UrlPath.parse('/api/d/e'): {
                Method.POST: Operation(mock_callback, 'd/e', (Method.POST, Method.PATCH)),
                Method.PATCH: Operation(mock_callback, 'd/e', (Method.POST, Method.PATCH)),
            }
        }

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
