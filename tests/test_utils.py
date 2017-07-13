import pytest

from odinweb import utils


class TestRandomString(object):
    @pytest.mark.parametrize('depth, expected_length', (
        (8, 2),
        (16, 3),
        (24, 4),
        (32, 6),
        (48, 8),
        (64, 11),
        (128, 22),
        (256, 43),
    ))
    def test_bit_length(self, depth, expected_length):
        actual = utils.random_string(depth)
        assert len(actual) == expected_length

    def test_invalid_bit_length(self):
        with pytest.raises(ValueError, message="Bit depth must be a multiple of 8"):
            utils.random_string(42)


@pytest.mark.parametrize('value, expected', (
    (None, ''),
    ('', ''),
    ('text/plain', 'text/plain'),
    ('text/plain; encoding=UTF-8', 'text/plain'),
    ('text/plain; encoding=UTF-8; x=y', 'text/plain'),
))
def test_parse_content_type(value, expected):
    actual = utils.parse_content_type(value)
    assert actual == expected


@pytest.mark.parametrize('value, expected', (
    ('', False),
    ('y', True),
    ('Yes', True),
    ('n', False),
    ('No', False),
    ('True', True),
    ('False', False),
    ('1', True),
    ('0', False),
    ('OK', True),
))
def test_to_bool(value, expected):
    actual = utils.to_bool(value)
    assert actual == expected


@pytest.mark.parametrize('base, updates, expected', (
    ({}, {}, {}),
    ({}, {'a': 'b'}, {'a': 'b'}),
    ({}, {'a': 0}, {'a': 0}),
    ({'a': 'b'}, {'a': 'c'}, {'a': 'c'}),
    ({'a': 'b'}, {'c': 'd'}, {'a': 'b', 'c': 'd'}),
    ({'a': 'b'}, {'c': None}, {'a': 'b'}),
))
def test_dict_filter_update(base, updates, expected):
    utils.dict_filter_update(base, updates)
    assert base == expected


@pytest.mark.parametrize('args, kwargs, expected', (
    ([], {}, {}),
    ([{'a': 'b'}], {}, {'a': 'b'}),
    ([{'a': 'b'}, {'a': 'b'}], {}, {'a': 'b'}),
    ([{'a': 'b'}, {'a': 'c'}], {}, {'a': 'c'}),
    ([{'a': 'b'}, {'c': None}], {}, {'a': 'b'}),
    ([{'a': 'b'}, {'c': 0}], {}, {'a': 'b', 'c': 0}),
    ([{'a': 'b'}], {'a': 'b'}, {'a': 'b'}),
    ([{'a': 'b'}], {'a': 'c'}, {'a': 'c'}),
    ([{'a': 'b'}], {'a': None}, {'a': 'b'}),
))
def test_dict_filter(args, kwargs, expected):
    actual = utils.dict_filter(*args, **kwargs)
    assert actual == expected
