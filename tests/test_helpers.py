from __future__ import absolute_import

import pytest

from odin.codecs import json_codec

from odinweb import content_type_resolvers
from odinweb import helpers
from odinweb.constants import HTTPStatus
from odinweb.data_structures import HttpResponse
from odinweb.exceptions import HttpError
from odinweb.testing import MockRequest

from .resources import User, Group


@pytest.mark.parametrize('value, expected', (
    (None, ''),
    ('', ''),
    ('text/plain', 'text/plain'),
    ('text/plain; encoding=UTF-8', 'text/plain'),
    ('text/plain; encoding=UTF-8; x=y', 'text/plain'),
))
def test_parse_content_type(value, expected):
    actual = helpers.parse_content_type(value)
    assert actual == expected


@pytest.mark.parametrize('http_request, expected', (
    (MockRequest(), 'application/json'),
    (MockRequest(headers={'accepts': 'text/html'}), 'text/html'),
    (MockRequest(headers={'content-type': 'text/plain'}), 'text/plain'),
    (MockRequest(headers={'accepts': 'text/html', 'content-type': 'text/plain'}), 'text/html'),
    (MockRequest(headers={'x-auth': '123'}), 'application/json'),
))
def test_resolve_content_type(http_request, expected):
    actual = helpers.resolve_content_type([
        content_type_resolvers.accepts_header(),
        content_type_resolvers.content_type_header(),
        content_type_resolvers.specific_default('application/json'),
    ], http_request)

    assert actual == expected


def test_get_resource():
    request = MockRequest(body='{"$": "tests.User", "id":10, "name": "Dave"}')
    request.request_codec = json_codec

    user = helpers.get_resource(request, User)

    assert isinstance(user, User)
    assert user.id == 10
    assert user.name == 'Dave'


def test_get_resource__multiple():
    request = MockRequest(body='[{"$": "tests.User", "id":10, "name": "Dave"}]')
    request.request_codec = json_codec

    users = helpers.get_resource(request, User, allow_multiple=True)

    assert len(users) == 1
    user = users[0]
    assert isinstance(user, User)
    assert user.id == 10
    assert user.name == 'Dave'


@pytest.mark.parametrize('body, error_code', (
    (b'\xFF', 40099),  # Invalid UTF-8
    (None, 40096),
    ('stuff', 40096),
    ('{"a":"b,}', 40096),
    ('[{"id":10, "name": "Dave"}]', 40097),
    ('[]', 40097),
    ('{"$": "wrong.User", "id":10, "name": "Dave"}', 40098),
    ('{"$": "tests.Group", "group_id":10, "name": "Dave"}', 40098),
    ('[{"$": "tests.Group", "group_id":10, "name": "Dave"}]', 40098),
))
def test_get_resource__codec_exceptions(body, error_code):
    request = MockRequest(body=body)

    with pytest.raises(HttpError) as exc_info:
        helpers.get_resource(request, User)

    assert exc_info.value.status == HTTPStatus.BAD_REQUEST
    assert exc_info.value.resource.code == error_code


class TestCreateResponse(object):
    def test_no_body(self):
        request = MockRequest()
        actual = helpers.create_response(request)

        assert isinstance(actual, HttpResponse)
        assert actual.status == HTTPStatus.NO_CONTENT
        assert actual.body is None

    def test_no_body_custom_status(self):
        request = MockRequest()
        actual = helpers.create_response(request, status=HTTPStatus.CREATED)

        assert isinstance(actual, HttpResponse)
        assert actual.status == HTTPStatus.CREATED
        assert actual.body is None

    def test_content(self):
        request = MockRequest()

        actual = helpers.create_response(request, {"foo": "bar"})

        assert isinstance(actual, HttpResponse)
        assert actual.status == HTTPStatus.OK
        assert actual.headers['Content-Type'] == json_codec.CONTENT_TYPE
        assert json_codec.json.loads(actual.body) == {"foo": "bar"}

    def test_content_custom_status(self):
        request = MockRequest()

        actual = helpers.create_response(request, {"foo": "bar"}, status=HTTPStatus.CREATED)

        assert isinstance(actual, HttpResponse)
        assert actual.status == HTTPStatus.CREATED
        assert actual.headers['Content-Type'] == json_codec.CONTENT_TYPE
        assert json_codec.json.loads(actual.body) == {"foo": "bar"}
