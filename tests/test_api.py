import pytest

from odinweb import api


class FakeApi(object):
    def __init__(self, result):
        self.result = result

    def __call__(self, *args, **kwargs):
        return self.result

    def api_routes(self):
        yield api.ApiRoute(['a', 'b'], ['GET'], self)
        yield api.ApiRoute(['d', 'e'], ['POST', 'PATCH'], self)


class TestApiContainer(object):
    @pytest.mark.parametrize('options,attr,value', (
        ({}, 'name', None),
        ({'name': 'foo'}, 'name', 'foo'),
        ({}, 'path_prefix', []),
        ({'name': 'foo'}, 'path_prefix', ['foo']),
        ({'path_prefix': ['bar']}, 'path_prefix', ['bar']),
    ))
    def test_options(self, options, attr, value):
        target = api.ApiContainer(**options)

        assert hasattr(target, attr)
        assert getattr(target, attr) == value

    def test_extra_option(self):
        with pytest.raises(TypeError, message="Got an unexpected keyword argument 'foo'"):
            api.ApiContainer(foo=1, name='test')

        with pytest.raises(TypeError):
            api.ApiContainer(foo=1, bar=2)

    def test_api_routes(self):
        fake_api = FakeApi('returned')
        target = api.ApiContainer(fake_api)

        actual = list(target.api_routes())

        assert actual == [
            api.ApiRoute(['a', 'b'], ['GET'], fake_api),
            api.ApiRoute(['d', 'e'], ['POST', 'PATCH'], fake_api),
        ]
