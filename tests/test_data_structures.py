from __future__ import absolute_import

import pytest
import sys

from odinweb.data_structures import HttpResponse, UrlPath, PathParam, _to_swagger, Param, Response, DefaultResponse, \
    MiddlewareList, DefaultResource
from odinweb.constants import Type, HTTPStatus, In

from .resources import User


def test_default_resource():
    # Creating a DefaultResource creates itself!
    assert DefaultResource is DefaultResource()


@pytest.mark.parametrize('args, expected', (
    ((None, None, None, None), {}),
    (({'foo': None}, None, None, None), {}),
    (({'foo': 'bar'}, None, None, None), {'foo': 'bar'}),
    ((None, 'Foo', None, None), {'description': 'Foo'}),
    ((None, 'Foo {name}', None, None), {'description': 'Foo UNKNOWN'}),
    ((None, 'Foo {name}', User, None), {'description': 'Foo User', 'schema': {'$ref': '#/definitions/tests.User'}}),
    (({'foo': 'bar'}, 'Foo {name}', User, {'eek': 'ook'}),
     {'foo': 'bar', 'description': 'Foo User', 'schema': {'$ref': '#/definitions/tests.User'}, 'eek': 'ook'}),
))
def test_to_swagger(args, expected):
    actual = _to_swagger(*args)
    assert actual == expected


class TestHttpResponse(object):
    @pytest.mark.parametrize('args, body, status, headers', (
        ((HTTPStatus.NOT_FOUND, None), HTTPStatus.NOT_FOUND.description, HTTPStatus.NOT_FOUND.value, {}),
        ((HTTPStatus.PROCESSING, None), HTTPStatus.PROCESSING.phrase, HTTPStatus.PROCESSING.value, {}),
        ((HTTPStatus.NOT_FOUND, {'foo': 1}), HTTPStatus.NOT_FOUND.description, HTTPStatus.NOT_FOUND.value, {'foo': 1}),
    ))
    def test_from_status(self, args, body, status, headers):
        target = HttpResponse.from_status(*args)

        assert target.body == body
        assert target.status == status
        assert target.headers == headers

    @pytest.mark.parametrize('args, body, status, headers', (
        (('foo',), 'foo', 200, {}),
        (('foo', HTTPStatus.NOT_FOUND), 'foo', 404, {}),
        (('foo', 400), 'foo', 400, {}),
        (('foo', HTTPStatus.NOT_FOUND, {'foo': 1}), 'foo', 404, {'foo': 1}),
    ))
    def test_init(self, args, body, status, headers):
        target = HttpResponse(*args)

        assert target.body == body
        assert target.status == status
        assert target.headers == headers

    def test_get(self):
        target = HttpResponse.from_status(HTTPStatus.OK, {'foo': 1})

        assert target['foo'] == 1

    def test_set(self):
        target = HttpResponse.from_status(HTTPStatus.OK, {'foo': 1})
        target['foo'] = 2

        assert target.headers == {'foo': 2}

    def test_set_content_type(self):
        target = HttpResponse.from_status(HTTPStatus.OK)
        target.set_content_type('text/html')

        assert target.headers == {'Content-Type': 'text/html'}


class TestUrlPath(object):
    @pytest.mark.parametrize('obj, expected', (
        (UrlPath('', 'foo'), ('', 'foo')),
        ('/foo', ('', 'foo')),
        (PathParam('name'), (PathParam('name'),)),
        (('', 'foo'), ('', 'foo')),
    ))
    def test_from_object(self, obj, expected):
        target = UrlPath.from_object(obj)

        assert target._nodes == expected

    @pytest.mark.parametrize('obj', (
        1,
        None,
        1.2,
        object()
    ))
    def test_from_object__value_error(self, obj):
        with pytest.raises(ValueError):
            UrlPath.from_object(obj)

    @pytest.mark.parametrize('path, expected', (
        ('', ()),
        ('/', ('',)),
        ('a', ('a',)),
        ('a/b', ('a', 'b')),
        ('/a/b', ('', 'a', 'b')),
        ('/a/b/', ('', 'a', 'b')),
        ('a/{b}/c', ('a', PathParam('b'), 'c')),
        ('a/{b:Integer}/c', ('a', PathParam('b', Type.Integer), 'c')),
    ))
    def test_parse(self, path, expected):
        target = UrlPath.parse(path)
        assert target._nodes == expected

    @pytest.mark.parametrize('path', (
        'a/{b/c',
        'a/b}/c',
        'a/{b:}/c',
        'a/{b:int}/c',
        'a/{b:eek}/c',
    ))
    def test_parse__raises_error(self, path):
        with pytest.raises(ValueError):
            UrlPath.parse(path)

    @pytest.mark.parametrize('path, expected', (
        (('',), '/'),
        (('a',), 'a'),
        (('', 'a'), '/a'),
        (('', 'a', 'b'), '/a/b'),
        (('', 'a', PathParam('b', None), 'c'), '/a/{b}/c'),
        (('', 'a', PathParam('b', Type.String), 'c'), '/a/{b:String}/c'),
    ))
    def test_str(self, path, expected):
        target = UrlPath(*path)

        assert str(target) == expected

    @pytest.mark.parametrize('a, b, expected', (
        (UrlPath.parse('a/b/c'), UrlPath.parse('d'), ('a', 'b', 'c', 'd')),
        (UrlPath.parse(''), UrlPath.parse('a/b'), ('a', 'b')),
        (UrlPath.parse('/a/b'), UrlPath.parse('c/d'), ('', 'a', 'b', 'c', 'd')),
        (UrlPath.parse('/a/b'), 'c', ('', 'a', 'b', 'c')),
        (UrlPath.parse('/a/b'), 'c/d', ('', 'a', 'b', 'c', 'd')),
        (UrlPath.parse('/a/b'), PathParam('c'), ('', 'a', 'b', PathParam('c'))),
        ('c', UrlPath.parse('a/b'), ('c', 'a', 'b')),
        ('c/d', UrlPath.parse('a/b'), ('c', 'd', 'a', 'b')),
        (PathParam('c'), UrlPath.parse('a/b'), (PathParam('c'), 'a', 'b')),
    ))
    def test_add(self, a, b, expected):
        actual = a + b
        assert actual._nodes == expected

    @pytest.mark.parametrize('a, b', (
        (UrlPath.parse('a/b/c'), UrlPath.parse('/d')),
        ('a/b/c', UrlPath.parse('/d')),
        (PathParam('c'), UrlPath.parse('/d')),
        (UrlPath.parse('/d'), 1),
        (1, UrlPath.parse('/d')),
    ))
    def test_add__error(self, a, b):
        with pytest.raises((ValueError, TypeError)):
            a + b

    @pytest.mark.parametrize('a, b, expected', (
        (UrlPath.parse('a/b/c'), UrlPath.parse('a/b/c'), True),
        (UrlPath.parse('/a/b/c'), UrlPath.parse('/a/b/c'), True),
        (UrlPath('a', 'b', 'c'), UrlPath.parse('a/b/c'), True),
        (UrlPath('', 'a', 'b', 'c'), UrlPath.parse('/a/b/c'), True),
        (UrlPath('a', 'b', 'c'), UrlPath.parse('/a/b/c'), False),
        (UrlPath('a', 'b', 'c'), 123, False),
    ))
    def test_eq(self, a, b, expected):
        assert (a == b) is expected

    @pytest.mark.parametrize('path, item, expected', (
        ('/a/b/c', 0, '/'),
        ('/a/b/c', 1, 'a'),
        ('/a/b/c', slice(1), '/'),
        ('/a/b/c', slice(None, 1), '/'),
        ('/a/b/c', slice(1, None), 'a/b/c'),
        ('/a/b/c', slice(-1, None), 'c'),
    ))
    def test_getitem(self, path, item, expected):
        target = UrlPath.parse(path)
        actual = str(target[item])
        assert actual == expected

    @pytest.mark.parametrize('target, expected', (
        (UrlPath.parse('/a/b/c'), True),
        (UrlPath.parse('a/b/c'), False),
        (UrlPath(), False),
    ))
    def test_is_absolute(self, target, expected):
        assert target.is_absolute == expected

    @pytest.mark.parametrize('args, expected', (
        (('a', 'b', 'c'), ()),
        (('a', PathParam('b'), 'c'), (PathParam('b'),)),
        (('a', PathParam('b'), PathParam('c')), (PathParam('b'), PathParam('c'))),
    ))
    def test_path_nodes(self, args, expected):
        target = UrlPath(*args)
        actual = tuple(target.path_nodes)
        assert actual == expected

    @pytest.mark.parametrize('path_node, expected', (
        (PathParam('name'), '{name:Integer}'),
        (PathParam('name', Type.String), '{name:String}'),
        (PathParam('name', None, None), '{name}'),
    ))
    def test_odinweb_node_formatter(self, path_node, expected):
        assert UrlPath.odinweb_node_formatter(path_node) == expected

    @pytest.mark.parametrize('url_path, formatter, expected', (
        (UrlPath('a', 'b', 'c'), None, 'a/b/c'),
        (UrlPath('', 'a', 'b', 'c'), None, '/a/b/c'),
        (UrlPath('', 'a', PathParam('b'), 'c'), None, '/a/{b:Integer}/c'),
        (UrlPath('', 'a', PathParam('b', None), 'c'), None, '/a/{b}/c'),
        (UrlPath('', 'a', PathParam('b', Type.String), 'c'), None, '/a/{b:String}/c'),
        (UrlPath('', 'a', PathParam('b', Type.String), 'c'), UrlPath.odinweb_node_formatter, '/a/{b:String}/c'),
    ))
    def test_format(self, url_path, formatter, expected):
        actual = url_path.format(formatter)
        assert actual == expected


class TestParam(object):
    @pytest.mark.parametrize('method, args, expected', (
        # Path
        (Param.path, ('foo',),
         {'name': 'foo', 'in': 'path', 'type': 'string', 'required': True}),
        (Param.path, ('foo', Type.Boolean, 'eek'),
         {'name': 'foo', 'in': 'path', 'type': 'boolean', 'description': 'eek', 'required': True}),
        (Param.path, ('foo', Type.Integer, None, 1, 0, 2),
         {'name': 'foo', 'in': 'path', 'type': 'integer', 'default': 1, 'minimum': 0, 'maximum': 2, 'required': True}),
        (Param.path, ('foo', Type.Number, None, None, None, None, ('a', 'b')),
         {'name': 'foo', 'in': 'path', 'type': 'number', 'enum': ('a', 'b'), 'required': True}),
        # Query
        (Param.query, ('foo',),
         {'name': 'foo', 'in': 'query', 'type': 'string'}),
        (Param.query, ('foo', Type.Boolean),
         {'name': 'foo', 'in': 'query', 'type': 'boolean'}),
        (Param.query, ('foo', Type.Integer),
         {'name': 'foo', 'in': 'query', 'type': 'integer'}),
        (Param.query, ('foo', Type.Number, 'eek'),
         {'name': 'foo', 'in': 'query', 'type': 'number', 'description': 'eek'}),
        (Param.query, ('foo', Type.String, None, False),
         {'name': 'foo', 'in': 'query', 'type': 'string', 'required': False}),
        (Param.query, ('foo', Type.String, None, None, 1, 0, 2),
         {'name': 'foo', 'in': 'query', 'type': 'string', 'default': 1, 'minimum': 0, 'maximum': 2}),
        (Param.query, ('foo', Type.String, None, None, None, None, None, ('a', 'b')),
         {'name': 'foo', 'in': 'query', 'type': 'string', 'enum': ('a', 'b')}),
        # Header
        (Param.header, ('foo',),
         {'name': 'foo', 'in': 'header', 'type': 'string'}),
        (Param.header, ('foo', Type.Boolean, 'eek'),
         {'name': 'foo', 'in': 'header', 'type': 'boolean', 'description': 'eek'}),
        (Param.header, ('foo', Type.Integer, None, 'eek'),
         {'name': 'foo', 'in': 'header', 'type': 'integer', 'default': 'eek'}),
        (Param.header, ('foo', Type.Integer, None, None, True),
         {'name': 'foo', 'in': 'header', 'type': 'integer', 'required': True}),
        # Body
        (Param.body, (),
         {'name': 'body', 'in': 'body', 'required': True}),
        (Param.body, ('foo',),
         {'name': 'body', 'in': 'body', 'description': 'foo', 'required': True}),
        (Param.body, ('foo', 'eek'),
         {'name': 'body', 'in': 'body', 'description': 'foo', 'default': 'eek', 'required': True}),
        (Param.body, (None, None, User),
         {'name': 'body', 'in': 'body', 'required': True, 'schema': {'$ref': '#/definitions/tests.User'}}),
        # Form
        (Param.form, ('foo',),
         {'name': 'foo', 'in': 'formData', 'type': 'string'}),
        (Param.form, ('foo', Type.Boolean),
         {'name': 'foo', 'in': 'formData', 'type': 'boolean'}),
        (Param.form, ('foo', Type.Integer),
         {'name': 'foo', 'in': 'formData', 'type': 'integer'}),
        (Param.form, ('foo', Type.Number, 'eek'),
         {'name': 'foo', 'in': 'formData', 'type': 'number', 'description': 'eek'}),
        (Param.form, ('foo', Type.String, None, False),
         {'name': 'foo', 'in': 'formData', 'type': 'string', 'required': False}),
        (Param.form, ('foo', Type.String, None, None, 1, 0, 2),
         {'name': 'foo', 'in': 'formData', 'type': 'string', 'default': 1, 'minimum': 0, 'maximum': 2}),
        (Param.form, ('foo', Type.String, None, None, None, None, None, ('a', 'b')),
         {'name': 'foo', 'in': 'formData', 'type': 'string', 'enum': ('a', 'b')}),
    ))
    def test_constructors(self, method, args, expected):
        target = method(*args)
        actual = target.to_swagger()
        assert actual == expected

    @pytest.mark.parametrize('method, args, expected', (
        (Param.path, ('foo', Type.String, None, None, 2, 1), ValueError),
        (Param.query, ('foo', Type.String, None, None, None, 2, 1), ValueError),
        (Param.form, ('foo', Type.String, None, None, None, 2, 1), ValueError),
    ))
    def test_constructors__errors(self, method, args, expected):
        with pytest.raises(expected):
            method(*args)

    def test_hash(self):
        a = Param('foo', In.Query)
        b = Param('foo', In.Query)
        assert hash(a) == hash(b)

        a = Param('foo', In.Query)
        b = Param('bar', In.Query)
        assert hash(a) != hash(b)

        a = Param('foo', In.Query)
        b = Param('foo', In.Path)
        assert hash(a) != hash(b)

    def test_str(self):
        target = Param('foo', In.Query)

        assert str(target) == 'Query param foo'

    def test_repr(self):
        target = Param('foo', In.Query, Type.Integer, foo='bar')

        assert repr(target) == "Param('foo', <In.Query: 'query'>, <Type.Integer: 'integer'>, None, {'foo': 'bar'})"


class TestResponse(object):
    def test_hash(self):
        a = Response(HTTPStatus.OK, 'Foo')
        b = Response(HTTPStatus.OK, 'Foo')
        assert hash(a) == hash(b)

        a = Response(HTTPStatus.OK, 'Foo')
        b = Response(HTTPStatus.NOT_FOUND, 'Foo')
        assert hash(a) != hash(b)

    def test_str(self):
        target = Response(HTTPStatus.OK)
        assert str(target) == "200 OK - Request fulfilled, document follows"

        target = Response(HTTPStatus.OK, 'Foo')
        assert str(target) == "200 OK - Foo"

        target = Response(HTTPStatus.ALREADY_REPORTED)
        assert str(target) == "208 Already Reported"

    def test_repr(self):
        target = Response(HTTPStatus.OK)

        assert repr(target) == "Response(<HTTPStatus.OK: 200>, None, <class 'odinweb.data_structures.DefaultResource'>)"

    def test_to_swagger(self):
        pass

    def test_to_swagger_default(self):
        target = DefaultResponse("Normal result")
        actual = target.to_swagger(User)
        assert actual == ('default', {
            'description': 'Normal result',
            'schema': {'$ref': '#/definitions/tests.User'}
        })


class MiddlewareA(object):
    def pre_dispatch(self):
        pass

    def post_swagger(self):
        pass


class MiddlewareB(object):
    def post_dispatch(self):
        pass

    def post_swagger(self):
        pass


class MiddlewareC(object):
    priority = 5

    def pre_dispatch(self):
        pass

    def post_dispatch(self):
        pass


@pytest.mark.skipif(sys.version_info < (3, 0), reason="requires python3.x")
class TestMiddlewareList(object):
    target = MiddlewareList((MiddlewareA(), MiddlewareB(), MiddlewareC()))

    def test_pre_dispatch(self):
        count = 0
        for actual, expected in zip(self.target.pre_dispatch, (MiddlewareC, MiddlewareA)):
            assert actual.__func__.__qualname__ == expected.pre_dispatch.__qualname__
            count += 1
        assert count == 2

    def test_post_dispatch(self):
        count = 0
        for actual, expected in zip(self.target.post_dispatch, (MiddlewareB,)):
            assert actual.__func__.__qualname__ == expected.post_dispatch.__qualname__
            count += 1
        assert count == 1

    def test_post_swagger(self):
        count = 0
        for actual, expected in zip(self.target.post_swagger, (MiddlewareA, MiddlewareB)):
            assert actual.__func__.__qualname__ == expected.post_swagger.__qualname__
            count += 1
        assert count == 2
