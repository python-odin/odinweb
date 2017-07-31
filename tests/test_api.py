# from __future__ import absolute_import
#
# import pytest
# import mock
#
# from odin.codecs import json_codec
# from odin.exceptions import ValidationError, CodecDecodeError
#
# from odinweb import api, containers
# from odinweb.constants import *
#
# from .resources import User
#
#
# def flatten_routes(api_routes):
#     """
#     Remove any iterators for easy comparisons in assert statements.
#     """
#     def flatten(api_route):
#         return api.ApiRoute(
#             ["<%s>" % p.name if isinstance(p, containers.PathNode) else p for p in api_route.path],
#             *api_route[1:]
#         )
#
#     return [flatten(r) for r in api_routes]
#
#
# #################################################
# # Mocks
#
# def mock_callback(self, request, **kwargs):
#     return 'returned'
#
#
# class UserApi(containers.ResourceApi):
#     resource = User
#
#     def __init__(self):
#         super(UserApi, self).__init__()
#         self.calls = []
#
#     @api.collection
#     def list_items(self, request):
#         self.calls.append('list_items')
#         return [User(1, 'Dave'), User(2, 'Bob')]
#
#     @api.detail
#     def get_item(self, request, resource_id):
#         self.calls.append('get_item')
#         return User(resource_id, 'Dave')
#
#     @api.action(url_path='start', methods=containers.Method.POST)
#     def start_item(self, request):
#         self.calls.append('start_item')
#         return self.create_response(request, status=202)
#
#     def mock_callback(self, request, **path_args):
#         self.calls.append('mock_callback')
#         return path_args
#
#
# class MockRequest(object):
#     def __init__(self, method='GET', headers=None, body=None, request_codec=None, response_codec=None):
#         self.body = body
#         self.method = method
#         self.headers = headers or {}
#         self.request_codec = request_codec or json_codec
#         self.response_codec = response_codec or json_codec
#
#
# class MockResourceApi(object):
#     def api_routes(self):
#         yield containers.ApiRoute(['a', 'b'], ('GET',), mock_callback)
#         yield containers.ApiRoute(['d', 'e'], ('POST', 'PATCH'), mock_callback)
#
#
# class MockApiInterface(containers.ApiInterfaceBase):
#     def parse_node(self, node):
#         if isinstance(node, containers.PathNode):
#             return "<%s>" % node.name
#         else:
#             return str(node)
#
#
# #################################################
# # Tests
#
# # class TestResourceApiMeta(object):
# #     def test_empty_api(self, mocker):
# #         mocker.patch('odinweb.decorators._route_count', 0)
# #
# #         class ExampleApi(api.ResourceApi):
# #             pass
# #
# #         assert ExampleApi._routes == []
# #
# #     def test_normal_api(self, mocker):
# #         mocker.patch('odinweb.decorators._route_count', 0)
# #
# #         class ExampleApi(api.ResourceApi):
# #             @api.collection
# #             def list_items(self, request):
# #                 pass
# #
# #             @api.detail
# #             def get_item(self, request, resource_id):
# #                 pass
# #
# #             @api.route(methods=('POST', 'PUT'))
# #             def create_item(self, request):
# #                 pass
# #
# #         assert ExampleApi._routes == [
# #             decorators.RouteDefinition(0, PathType.Collection, ('GET',), None, ExampleApi.__dict__['list_items']),
# #             decorators.RouteDefinition(1, PathType.Resource, ('GET',), None, ExampleApi.__dict__['get_item']),
# #             decorators.RouteDefinition(2, PathType.Collection, ('POST', 'PUT'), None, ExampleApi.__dict__['create_item']),
# #         ]
# #
# #     def test_sub_classed_api(self, mocker):
# #         mocker.patch('odinweb.decorators._route_count', 0)
# #
# #         class SuperApi(api.ResourceApi):
# #             @api.collection
# #             def list_items(self, request):
# #                 pass
# #
# #         class SubApi(SuperApi):
# #             @api.detail
# #             def get_item(self, request, resource_id):
# #                 pass
# #
# #             @api.route(methods=('POST', 'PUT'))
# #             def create_item(self, request):
# #                 pass
# #
# #         assert SubApi._routes == [
# #             decorators.RouteDefinition(0, PathType.Collection, ('GET',), None, SuperApi.__dict__['list_items']),
# #             decorators.RouteDefinition(1, PathType.Resource, ('GET',), None, SubApi.__dict__['get_item']),
# #             decorators.RouteDefinition(2, PathType.Collection, ('POST', 'PUT'), None, SubApi.__dict__['create_item']),
# #         ]
#
#
# # class TestResourceApi(object):
# #     def test_api_name__default(self):
# #         target = UserApi()
# #
# #         assert target.api_name == 'user'
# #
# #     def test_api_name__custom(self):
# #         class Example(api.ResourceApi):
# #             resource = User
# #             api_name = 'users'
# #
# #         target = Example()
# #
# #         assert target.api_name == 'users'
# #
# #     def test_debug_enabled__no_parent(self):
# #         target = UserApi()
# #
# #         assert not target.debug_enabled
# #
# #     def test_debug_enabled__with_parent(self):
# #         parent = mock.Mock()
# #         parent.debug_enabled = True
# #
# #         target = UserApi()
# #         target.parent = parent
# #
# #         assert target.debug_enabled
# #
# #     def test_api_routes(self):
# #         target = UserApi()
# #         target._wrap_callback = lambda callback, methods: callback
# #
# #         actual = flatten_routes(target.api_routes())
# #
# #         assert actual == [
# #             api.ApiRoute(['user'], ('GET',), UserApi.__dict__['list_items']),
# #             api.ApiRoute(['user', '<resource_id>'], ('GET',), UserApi.__dict__['get_item']),
# #             api.ApiRoute(['user', '<resource_id>', 'start'], ('POST',), UserApi.__dict__['start_item']),
# #         ]
# #
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
#
#
# class TestApiContainer(object):
#     @pytest.mark.parametrize('options,attr,value', (
#         ({}, 'name', None),
#         ({'name': 'foo'}, 'name', 'foo'),
#         ({}, 'path_prefix', []),
#         ({'name': 'foo'}, 'path_prefix', ['foo']),
#         ({'path_prefix': ['bar']}, 'path_prefix', ['bar']),
#     ))
#     def test_options(self, options, attr, value):
#         target = containers.ApiContainer(**options)
#
#         assert hasattr(target, attr)
#         assert getattr(target, attr) == value
#
#     def test_extra_option(self):
#         with pytest.raises(TypeError, message="Got an unexpected keyword argument 'foo'"):
#             containers.ApiContainer(foo=1, name='test')
#
#         with pytest.raises(TypeError):
#             containers.ApiContainer(foo=1, bar=2)
#
#     def test_api_routes(self):
#         target = containers.ApiContainer(MockResourceApi(), path_prefix=['z'])
#
#         actual = flatten_routes(target.api_routes())
#         assert actual == [
#             containers.ApiRoute(['z', 'a', 'b'], ('GET',), mock_callback),
#             containers.ApiRoute(['z', 'd', 'e'], ('POST', 'PATCH'), mock_callback),
#         ]
#
#     def test_additional_routes(self):
#         target = containers.ApiContainer(path_prefix=['z'])
#         target.additional_routes = [
#             containers.ApiRoute(['f'], ['GET'], None)
#         ]
#
#         actual = flatten_routes(target.api_routes())
#         assert actual == [
#             containers.ApiRoute(['z', 'f'], ['GET'], None),
#         ]
#
#     def test_callable_additional_routes(self):
#         target = containers.ApiContainer(path_prefix=['z'])
#         target.additional_routes = lambda: [
#             containers.ApiRoute(['f'], ['GET'], None)
#         ]
#
#         actual = flatten_routes(target.api_routes())
#         assert actual == [
#             containers.ApiRoute(['z', 'f'], ['GET'], None),
#         ]
#
#
# class TestApiCollection(object):
#     """
#     Actually test with ApiVersion is this is a thin layer over a collection.
#     """
#     def test_debug_enabled__no_parent(self):
#         target = containers.ApiVersion()
#
#         assert not target.debug_enabled
#
#     def test_debug_enabled__with_parent(self):
#         parent = mock.Mock()
#         parent.debug_enabled = True
#
#         target = containers.ApiVersion()
#         target.parent = parent
#
#         assert target.debug_enabled
#
#     @pytest.mark.parametrize('options,version,name,path_prefix', (
#         ({}, 1, 'v1', ['v1']),
#         ({'version': 2}, 2, 'v2', ['v2']),
#         ({'version': 3, 'name': 'version-3'}, 3, 'version-3', ['version-3']),
#     ))
#     def test_version_options(self, options, version, name, path_prefix):
#         target = containers.ApiVersion(**options)
#
#         assert target.version == version
#         assert target.name == name
#         assert target.path_prefix == path_prefix
#
#
# class TestApiInterfaceBase(object):
#     @pytest.mark.parametrize('options,name,debug_enabled,path_prefix', (
#         ({}, 'api', False, ['', 'api']),
#         ({'name': '!api'}, '!api', False, ['', '!api']),
#         ({'url_prefix': '/my-app/'}, 'api', False, ['/my-app', 'api']),
#         ({'debug_enabled': True}, 'api', True, ['', 'api']),
#     ))
#     def test_options(self, options, name, debug_enabled, path_prefix):
#         target = containers.ApiInterfaceBase(**options)
#
#         assert target.name == name
#         assert target.debug_enabled == debug_enabled
#         assert target.path_prefix == path_prefix
#
#     # @pytest.mark.parametrize('options,api_routes', (
#     #     ({}, [
#     #         containers.ApiRoute('/api/a/b', ('GET',), mock_callback),
#     #         containers.ApiRoute('/api/d/e', ('POST', 'PATCH'), mock_callback),
#     #     ]),
#     #     ({'url_prefix': 'my-app'}, [
#     #         containers.ApiRoute('my-app/api/a/b', ('GET',), mock_callback),
#     #         containers.ApiRoute('my-app/api/d/e', ('POST', 'PATCH'), mock_callback),
#     #     ]),
#     #     ({'name': '!api', 'url_prefix': '/my-app'}, [
#     #         containers.ApiRoute('/my-app/!api/a/b', ('GET',), mock_callback),
#     #         containers.ApiRoute('/my-app/!api/d/e', ('POST', 'PATCH'), mock_callback),
#     #     ]),
#     # ))
#     # def test_build_routes(self, options, api_routes):
#     #     target = MockApiInterface(MockResourceApi(), **options)
#     #
#     #     actual = list(target.build_routes())
#     #     assert actual == api_routes
#
#     def test_ensure_parse_node_is_implemented(self):
#         target = containers.ApiInterfaceBase()
#
#         with pytest.raises(NotImplementedError):
#             target.parse_node(None)
#
#
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
