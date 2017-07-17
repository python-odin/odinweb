import pytest

from odinweb import decorators
from odinweb.constants import *
from odinweb.testing import MockRequest


@pytest.mark.parametrize('decorator, definition', (
    (decorators.route, (PathType.Collection, (Method.GET.value,), None)),
    (decorators.resource_route, (PathType.Resource, (Method.GET.value,), None)),
    (decorators.listing, (PathType.Collection, (Method.GET.value,), None)),
    (decorators.create, (PathType.Collection, (Method.POST.value,), None)),
    (decorators.detail, (PathType.Resource, (Method.GET.value,), None)),
    (decorators.update, (PathType.Resource, (Method.PUT.value,), None)),
    (decorators.patch, (PathType.Resource, (Method.PATCH.value,), None)),
    (decorators.delete, (PathType.Resource, (Method.DELETE.value,), None)),
))
def test_endpoint_decorators(decorator, definition):
    @decorator
    def target(self, request):
        pass

    assert isinstance(target.route, decorators.RouteDefinition)
    assert target.route.route_number == decorators._route_count - 1
    assert target.route[1:-1] == definition
    assert target.route[-1] == target


class TestListing(object):
    @pytest.mark.parametrize('options, offset, limit', (
        ({}, 0, 50),
        ({'default_offset': 10}, 10, 50),
        ({'default_limit': 10}, 0, 10),
        ({'default_offset': 10, 'default_limit': 20}, 10, 20),
    ))
    def test_documentation_applied(self, options, offset, limit):
        @decorators.listing(**options)
        def my_func():
            pass

        assert getattr(my_func, '__docs')._parameters['query:offset']['default'] == offset
        assert getattr(my_func, '__docs')._parameters['query:limit']['default'] == limit
        assert not getattr(my_func, '__docs')._parameters['query:bare']['default']

    @pytest.mark.parametrize('options, query, offset, limit, bare', (
        ({}, {}, 0, 50, False),
        ({}, {'offset': 10}, 10, 50, False),
        ({}, {'limit': 20}, 0, 20, False),
        ({}, {'bare': 'F'}, 0, 50, False),
        ({}, {'bare': 'T'}, 0, 50, True),
        ({}, {'bare': 'yes'}, 0, 50, True),
        ({}, {'offset': 10, 'limit': 20, 'bare': '1'}, 10, 20, True),
        # Max offset/limit
        ({'max_offset': 10, 'max_limit': 100}, {}, 0, 50, False),
        ({'max_offset': 10, 'max_limit': 100}, {'offset': 10, 'limit': 100}, 10, 100, False),
        ({'max_offset': 10, 'max_limit': 100}, {'offset': 11, 'limit': 101}, 10, 100, False),
        ({'max_offset': 10, 'max_limit': 100}, {'offset': 20, 'limit': 150}, 10, 100, False),
        # Silly values?
        ({}, {'offset': -1}, 0, 50, False),
        ({}, {'limit': -1}, 0, 1, False),
        ({}, {'limit': 0}, 0, 1, False),
        ({}, {'offset': -1, 'limit': -1}, 0, 1, False),
    ))
    def test_options_handled(self, options, query, offset, limit, bare):
        mock_request = MockRequest(query=query)

        @decorators.listing(**options)
        def my_func(self, request, **kwargs):
            assert request is mock_request
            assert kwargs['offset'] == offset
            assert kwargs['limit'] == limit
            assert kwargs['foo'] == 'bar'
            return [1, 2, 3]

        result = my_func(None, mock_request, foo='bar')

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

        @decorators.listing
        def my_func(self, request, foo, offset, limit):
            assert foo == 'bar'
            assert offset == 0
            assert limit == 50
            return [1, 2, 3], 5

        result = my_func(None, mock_request, foo='bar')

        assert isinstance(result, decorators.Listing)
        assert result.results == [1, 2, 3]
        assert result.offset == 0
        assert result.limit == 50
        assert result.total_count == 5
