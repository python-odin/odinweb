import pytest

from odinweb import decorators
from odinweb.constants import *


@pytest.mark.parametrize('decorator,definition', (
    (decorators.route, (PathType.Collection, (GET,), None)),
    (decorators.resource_route, (PathType.Resource, (GET,), None)),
    (decorators.listing, (PathType.Collection, (GET,), None)),
    (decorators.create, (PathType.Collection, (POST,), None)),
    (decorators.detail, (PathType.Resource, (GET,), None)),
    (decorators.update, (PathType.Resource, (PUT,), None)),
    (decorators.patch, (PathType.Resource, (PATCH,), None)),
    (decorators.delete, (PathType.Resource, (DELETE,), None)),
))
def test_endpoint_decorators(decorator, definition):
    @decorator
    def target(request):
        pass

    assert target.route.route_number == decorators._route_count - 1
    assert target.route[1:-1] == definition
    assert target.route[-1] == target
