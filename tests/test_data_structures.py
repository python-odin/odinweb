import pytest

from odinweb.data_structures import HttpResponse, UrlPath, PathNode, Type, HTTPStatus


class TestHttpResponse(object):
    @pytest.mark.parametrize('target, body, status, headers', (
        (HttpResponse('foo'), 'foo', 200, {}),
        (HttpResponse('foo', HTTPStatus.UNAUTHORIZED), 'foo', 401, {}),
        (HttpResponse('foo', headers={'bar': 'eek'}), 'foo', 200, {'bar': 'eek'}),
    ))
    def test_init(self, target, body, status, headers):
        assert target.body == body
        assert target.status == status
        assert target.headers == headers


class TestUrlPath(object):
    def test_construct(self):
        target = UrlPath('a', 'b', 'c')

        assert target._nodes == ('a', 'b', 'c')

    @pytest.mark.parametrize('path, expected', (
        ('', ()),
        ('/', ('',)),
        ('a', ('a',)),
        ('a/b', ('a', 'b')),
        ('/a/b', ('', 'a', 'b')),
        ('/a/b/', ('', 'a', 'b')),
        ('a/{b}/c', ('a', PathNode('b'), 'c')),
        ('a/{b:integer}/c', ('a', PathNode('b', Type.Integer), 'c')),
    ))
    def test_parse(self, path, expected):
        target = UrlPath.parse(path)

        assert target._nodes == expected

    @pytest.mark.parametrize('path, expected', (
        (('a',), 'a'),
        (('', 'a'), '/a'),
        (('', 'a', 'b'), '/a/b'),
        (('', 'a', PathNode('b', None), 'c'), '/a/{b}/c'),
        (('', 'a', PathNode('b', Type.String), 'c'), '/a/{b:string}/c'),
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
        (UrlPath.parse('/a/b'), PathNode('c'), ('', 'a', 'b', PathNode('c'))),
        ('c', UrlPath.parse('a/b'), ('c', 'a', 'b')),
        ('c/d', UrlPath.parse('a/b'), ('c', 'd', 'a', 'b')),
        (PathNode('c'), UrlPath.parse('a/b'),  (PathNode('c'), 'a', 'b')),
    ))
    def test_add(self, a, b, expected):
        actual = a + b
        assert actual._nodes == expected

    @pytest.mark.parametrize('a, b', (
        (UrlPath.parse('a/b/c'), UrlPath.parse('/d')),
        ('a/b/c', UrlPath.parse('/d')),
        (PathNode('c'), UrlPath.parse('/d')),
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
    def test_equals(self, a, b, expected):
        assert (a == b) is expected

    def test_is_absolute(self):
        assert UrlPath.parse('/a/b/c').is_absolute
        assert not UrlPath.parse('a/b/c').is_absolute
        assert not UrlPath().is_absolute

    @pytest.mark.parametrize('path_node, expected', (
        (PathNode('name'), '{name}'),
        (PathNode('name', Type.String), '{name}'),
        (PathNode('name', None, None), '{name}'),
    ))
    def test_swagger_node_formatter(self, path_node, expected):
        assert UrlPath.swagger_node_formatter(path_node) == expected

    @pytest.mark.parametrize('path_node, expected', (
        (PathNode('name'), '{name:integer}'),
        (PathNode('name', Type.String), '{name:string}'),
        (PathNode('name', None, None), '{name}'),
    ))
    def test_odinweb_node_formatter(self, path_node, expected):
        assert UrlPath.odinweb_node_formatter(path_node) == expected

    @pytest.mark.parametrize('url_path, expected', (
        (UrlPath('a', 'b', 'c'), 'a/b/c'),
        (UrlPath('', 'a', 'b', 'c'), '/a/b/c'),
        (UrlPath('', 'a', PathNode('b'), 'c'), '/a/{b:integer}/c'),
        (UrlPath('', 'a', PathNode('b', None), 'c'), '/a/{b}/c'),
        (UrlPath('', 'a', PathNode('b', Type.String), 'c'), '/a/{b:string}/c'),
    ))
    def test_format(self, url_path, expected):
        actual = url_path.format(UrlPath.odinweb_node_formatter)
        assert actual == expected
