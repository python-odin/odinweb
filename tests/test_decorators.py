from __future__ import absolute_import

import pytest

from collections import defaultdict

from odinweb import decorators
from odinweb.constants import *
from odinweb.data_structures import NoPath, Param, HttpResponse
from odinweb.exceptions import HttpError
from odinweb.testing import MockRequest

from .resources import User


class TestOperation(object):
    def test_init(self):
        @decorators.Operation
        def target(request):
            """
            Test target
            """

        assert isinstance(target, decorators.Operation)
        assert target.url_path == NoPath
        assert target.methods == (Method.GET,)

    def test_str(self):
        @decorators.Operation(path="test/{id}/start")
        def target(request):
            """
            Test target
            """

        assert "tests.test_decorators.target - GET test/{id:Integer}/start" == str(target)

    def test_repr(self):
        @decorators.Operation(path="test/{id}/start")
        def target(request):
            """
            Test target
            """

        assert "Operation('tests.test_decorators.target', " \
               "UrlPath('test', PathParam(name='id', type=<Type.Integer: 'integer:int32'>, type_args=None), 'start'), " \
               "(<Method.GET: 'GET'>,))" == repr(target)

    def test_unbound(self):
        @decorators.Operation(tags=('eek', 'bar'))
        def target(request):
            """
            Test target
            """
            return 'foo'

        request = MockRequest()
        assert target.resource is None
        assert not target.is_bound
        assert target.tags == {'eek', 'bar'}

        actual = target(request, {})
        assert actual == 'foo'

    def test_bind_to_instance(self):
        @decorators.Operation(tags=('eek', 'bar'))
        def target(binding, request):
            """
            Test target
            """
            assert binding == api
            return 'foo'

        class MockApi(object):
            def __init__(self):
                self.call_count = defaultdict(int)
                self.resource = User
                self.tags = {'bar'}

            def pre_dispatch(self, request, path_args):
                self.call_count['pre_dispatch'] += 1

            def post_dispatch(self, request, response):
                self.call_count['post_dispatch'] += 1
                return response

        api = MockApi()
        request = MockRequest()
        target.bind_to_instance(api)
        assert target.binding == api
        assert target.resource is User
        assert target.is_bound
        assert target.tags == {'eek', 'bar'}

        actual = target(request, {})
        assert actual == 'foo'
        assert api.call_count == {'pre_dispatch': 1, 'post_dispatch': 1}

    @pytest.mark.parametrize('decorator, init_args, expected', (
        (decorators.Operation, {}, {}),
        (decorators.Operation, {'tags': 'foo'}, {'tags': ['foo']}),
    ))
    def test_to_swagger(self, decorator, init_args, expected):
        @decorator(**init_args)
        def my_func(request):
            """
            My Func
            """
            pass

        # Set some common defaults
        expected.setdefault('operationId', 'tests.test_decorators.my_func')
        expected.setdefault('description', 'My Func')
        expected.setdefault('responses', {'default': {
            'description': 'Unhandled error',
            'schema': {'$ref': '#/definitions/Error'}
        }})

        actual = my_func.to_swagger()
        assert actual == expected


class TestWrappedListOperation(object):
    @pytest.mark.parametrize('options, offset, limit', (
        ({}, 0, 50),
        ({'default_limit': 10}, 0, 10),
    ))
    def test_documentation_applied(self, options, offset, limit):
        @decorators.listing(**options)
        def my_func(request):
            pass

        assert my_func.default_offset == offset
        assert my_func.default_limit == limit

    @pytest.mark.parametrize('options, query, offset, limit, bare', (
        ({}, {}, 0, 50, False),
        ({}, {'offset': 10}, 10, 50, False),
        ({}, {'limit': 20}, 0, 20, False),
        ({}, {'bare': 'F'}, 0, 50, False),
        ({}, {'bare': 'T'}, 0, 50, True),
        ({}, {'bare': 'yes'}, 0, 50, True),
        ({}, {'offset': 10, 'limit': 20, 'bare': '1'}, 10, 20, True),
        # Max limit
        ({'max_limit': 100}, {}, 0, 50, False),
        ({'max_limit': 100}, {'offset': 10, 'limit': 100}, 10, 100, False),
        ({'max_limit': 100}, {'offset': 10, 'limit': 102}, 10, 100, False),
        # Silly values?
        ({}, {'offset': -1}, 0, 50, False),
        ({}, {'limit': -1}, 0, 1, False),
        ({}, {'limit': 0}, 0, 1, False),
        ({}, {'offset': -1, 'limit': -1}, 0, 1, False),
    ))
    def test_options_handled(self, options, query, offset, limit, bare):
        mock_request = MockRequest(query=query)

        @decorators.WrappedListOperation(**options)
        def my_func(request, **kwargs):
            assert request is mock_request
            assert kwargs['offset'] == offset
            assert kwargs['limit'] == limit
            assert kwargs['foo'] == 'bar'
            return [1, 2, 3]

        result = my_func(mock_request, {'foo': 'bar'})

        if bare:
            assert result == [1, 2, 3]
        else:
            assert isinstance(result, decorators.Listing)
            assert result.results == [1, 2, 3]
            assert result.offset == offset
            assert result.limit == limit
            assert result.total_count is None

    def test_returning_total_count(self):
        mock_request = MockRequest()

        @decorators.WrappedListOperation
        def my_func(request, foo, offset, limit):
            assert foo == 'bar'
            assert offset == 0
            assert limit == 50
            return [1, 2, 3], 5

        result = my_func(mock_request, {'foo': 'bar'})

        assert isinstance(result, decorators.Listing)
        assert result.results == [1, 2, 3]
        assert result.offset == 0
        assert result.limit == 50
        assert result.total_count == 5


class TestListOperation(object):
    @pytest.mark.parametrize('options, offset, limit', (
        ({}, 0, 50),
        ({'default_limit': 10}, 0, 10),
    ))
    def test_documentation_applied(self, options, offset, limit):
        options.setdefault('use_wrapper', False)

        @decorators.listing(**options)
        def my_func(request):
            pass

        assert my_func.default_offset == offset
        assert my_func.default_limit == limit

    @pytest.mark.parametrize('options, query, offset, limit', (
        ({}, {}, 0, 50),
        ({}, {'offset': 10}, 10, 50),
        ({}, {'limit': 20}, 0, 20),
        ({}, {'offset': 10, 'limit': 20}, 10, 20),
        # Max limit
        ({'max_limit': 100}, {}, 0, 50),
        ({'max_limit': 100}, {'offset': 10, 'limit': 100}, 10, 100),
        ({'max_limit': 100}, {'offset': 10, 'limit': 102}, 10, 100),
        # Silly values?
        ({}, {'offset': -1}, 0, 50),
        ({}, {'limit': -1}, 0, 1),
        ({}, {'limit': 0}, 0, 1),
        ({}, {'offset': -1, 'limit': -1}, 0, 1),
    ))
    def test_options_handled(self, options, query, offset, limit):
        mock_request = MockRequest(query=query)

        @decorators.ListOperation(**options)
        def my_func(request, **kwargs):
            assert request is mock_request
            assert kwargs['offset'] == offset
            assert kwargs['limit'] == limit
            assert kwargs['foo'] == 'bar'
            return [1, 2, 3]

        result = my_func(mock_request, {'foo': 'bar'})

        assert isinstance(result, HttpResponse)
        assert result.body == '[1, 2, 3]'
        assert result['X-Page-Offset'] == str(offset)
        assert result['X-Page-Limit'] == str(limit)
        assert 'X-Total-Count' not in result.headers

    def test_returning_total_count(self):
        mock_request = MockRequest()

        @decorators.ListOperation
        def my_func(request, foo, offset, limit):
            assert foo == 'bar'
            assert offset == 0
            assert limit == 50
            return [1, 2, 3], 5

        result = my_func(mock_request, {'foo': 'bar'})

        assert isinstance(result, HttpResponse)
        assert result.body == '[1, 2, 3]'
        assert result['X-Page-Offset'] == '0'
        assert result['X-Page-Limit'] == '50'
        assert result['X-Total-Count'] == '5'


class TestResourceOperation(object):
    def test_documentation_applied(self):
        @decorators.ResourceOperation(resource=User)
        def my_func(request, user):
            pass

        assert Param.body() in my_func.parameters

    def test_execute(self):
        @decorators.ResourceOperation(resource=User)
        def my_func(request, user):
            assert isinstance(user, User)
            assert user.name == "Stephen"

        request = MockRequest(body='{"id": 1, "name": "Stephen"}')
        my_func(request, {})

    def test_execute__invalid(self):
        @decorators.ResourceOperation(resource=User)
        def my_func(request, user):
            assert isinstance(user, User)
            assert user.name == "Stephen"

        request = MockRequest(body='{"id": 1, "name": "Stephen"')
        with pytest.raises(HttpError):
            my_func(request, {})


@pytest.mark.parametrize('decorator, klass, method', (
    (decorators.listing, decorators.WrappedListOperation, Method.GET),
    (decorators.create, decorators.ResourceOperation, Method.POST),
    (decorators.detail, decorators.Operation, Method.GET),
    (decorators.update, decorators.ResourceOperation, Method.PUT),
    (decorators.patch, decorators.ResourceOperation, Method.PATCH),
    (decorators.delete, decorators.Operation, Method.DELETE),
))
def test_endpoint_decorators(decorator, klass, method):
    @decorator
    def target(request):
        pass

    assert isinstance(target, klass)
    assert target.methods == (method,)
