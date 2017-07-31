import pytest

from odinweb import content_type_resolvers
from odinweb.testing import MockRequest


@pytest.mark.parametrize('resolver, args, http_request, expected', (
    # Accepts Header
    (content_type_resolvers.accepts_header, (), MockRequest(headers={'accepts': 'application/json'}), 'application/json'),
    (content_type_resolvers.accepts_header, (), MockRequest(headers={'content-type': 'application/json'}), None),
    # Content type header
    (content_type_resolvers.content_type_header, (), MockRequest(headers={'accepts': 'application/json'}), None),
    (content_type_resolvers.content_type_header, (), MockRequest(headers={'content-type': 'application/json'}), 'application/json'),
    # Specific default
    (content_type_resolvers.specific_default, ('application/json',), MockRequest(headers={'accepts': 'text/html'}), 'application/json'),
    (content_type_resolvers.specific_default, ('application/json',), MockRequest(headers={'content-type': 'text/html'}), 'application/json'),
    (content_type_resolvers.specific_default, ('application/json',), MockRequest(), 'application/json'),
))
def test_resolvers(resolver, args, http_request, expected):
    instance = resolver(*args)
    actual = instance(http_request)
    assert actual == expected
