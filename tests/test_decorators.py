import pytest

from odinweb import decorators
from odinweb import constants


@pytest.mark.parametrize('decorator,definition', (
    (decorators.route, (constants.PATH_TYPE_COLLECTION, (constants.GET,), None)),
    (decorators.resource_route, (constants.PATH_TYPE_RESOURCE, (constants.GET,), None)),
    (decorators.listing, (constants.PATH_TYPE_COLLECTION, (constants.GET,), None)),
    (decorators.create, (constants.PATH_TYPE_COLLECTION, (constants.POST,), None)),
    (decorators.detail, (constants.PATH_TYPE_RESOURCE, (constants.GET,), None)),
    (decorators.update, (constants.PATH_TYPE_RESOURCE, (constants.PUT,), None)),
    (decorators.patch, (constants.PATH_TYPE_RESOURCE, (constants.PATCH,), None)),
    (decorators.delete, (constants.PATH_TYPE_RESOURCE, (constants.DELETE,), None)),
))
def test_endpoint_decorators(decorator, definition):
    @decorator
    def target(request):
        pass

    assert target.route.route_number == decorators._route_count - 1
    assert target.route[1:-1] == definition
    assert target.route[-1] == target
