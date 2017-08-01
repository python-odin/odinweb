import pytest

from odinweb import swagger

from .resources import User


def test_resource_definition():
    actual = swagger.resource_definition(User)

    assert actual == {
        'type': 'object',
        'properties': {
            'id': {'type': 'integer', 'format': 'int64'},
            'name': {'type': 'string'},
            'email': {'type': 'string', 'description': 'Users email'},
            'role': {'type': 'string', 'enum': ['admin', 'manager', 'user']},
        }
    }


class TestSwaggerSpec(object):
    @pytest.mark.parametrize('options, title, enable_ui, host, schemes', (
        ({'title': 'Test'}, 'Test', False, None, None),
        ({'title': 'Test', 'enable_ui': True}, 'Test', True, None, None),
        ({'title': 'Test', 'host': 'localhost'}, 'Test', False, 'localhost', None),
        ({'title': 'Test', 'schemes': ('http', 'https')}, 'Test', False, None, ('http', 'https')),
    ))
    def test_configure(self, options, title, enable_ui, host, schemes):
        target = swagger.SwaggerSpec(**options)

        assert target.title == title
        assert target.enable_ui == enable_ui
        assert target.host == host
        assert target.schemes == schemes
