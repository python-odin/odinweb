from odinweb import resources


def test_any_field():
    target = resources.AnyField()

    actual = target.to_python('abc')  # Should do nothing to value.
    assert actual == 'abc'
