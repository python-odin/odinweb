import pytest

from odinweb import swagger, _compat
from odinweb.constants import Type, HTTPStatus, Method
from odinweb.containers import ApiInterfaceBase, ApiContainer, ApiVersion
from odinweb.data_structures import UrlPath, Param
from odinweb.decorators import Operation
from odinweb.exceptions import HttpError
from odinweb.testing import MockRequest

from .resources import User, Group


class TestResourceDefinition:
    def test_basic_definition(self):
        actual = swagger.resource_definition(User)

        assert actual == {
            'type': 'object',
            'properties': {
                'id': {'type': 'integer', 'format': 'int64'},
                'name': {'type': 'string'},
                'email': {'type': 'string', 'format': 'email', 'description': 'Users email'},
                'role': {'type': 'string', 'enum': ['admin', 'manager', 'user']},
            }
        }

    def test_with_calculated_field(self):
        actual = swagger.resource_definition(Group)

        assert actual == {
            'type': 'object',
            'properties': {
                'group_id': {'type': 'integer', 'format': 'int64'},
                'name': {'type': 'string'},
                'title': {'readOnly': True},
            }
        }


class TestSwaggerSpec(object):
    @pytest.mark.parametrize('options, title, enabled, enable_ui, host, schemes', (
        ({'title': 'Test'}, 'Test', True, False, None, set()),
        ({'title': 'Test', 'enabled': False}, 'Test', False, False, None, set()),
        ({'title': 'Test', 'enable_ui': True}, 'Test', True, True, None, set()),
        ({'title': 'Test', 'enabled': False, 'enable_ui': True}, 'Test', False, False, None, set()),
        ({'title': 'Test', 'host': 'localhost'}, 'Test', True, False, 'localhost', set()),
        ({'title': 'Test', 'schemes': ('http', 'https')}, 'Test', True, False, None, {'http', 'https'}),
        ({'title': 'Test', 'schemes': 'http'}, 'Test', True, False, None, {'http'}),
    ))
    def test_configure(self, options, title, enabled, enable_ui, host, schemes):
        target = swagger.SwaggerSpec(**options)

        assert target.title == title
        assert target.enabled == enabled
        assert target.enable_ui == enable_ui
        assert target.host == host
        assert target.schemes == schemes

    def test_base_path(self):
        target = swagger.SwaggerSpec(title="")

        ApiInterfaceBase(
            ApiContainer(
                ApiContainer(
                    ApiContainer(
                        target
                    ),
                    name='b'
                ),
                name='a'
            )
        )

        assert UrlPath.parse("/api/a/b") == target.base_path
        assert UrlPath.parse("/api/a/b/swagger") == target.swagger_path

    def test_cenancestor(self):
        target = swagger.SwaggerSpec(title="")

        expected = ApiInterfaceBase(
            ApiContainer(
                ApiContainer(
                    ApiContainer(),
                    target,
                    name='b'
                ),
                name='a'
            )
        )

        assert target.cenancestor is expected

    def test_generate_parameters(self):
        actual = swagger.SwaggerSpec.generate_parameters(UrlPath.parse('/api/a/{b}/c/{d:String}'))
        assert actual == [{
            'name': 'b',
            'in': 'path',
            'type': 'integer',
            'required': True,
        }, {
            'name': 'd',
            'in': 'path',
            'type': 'string',
            'required': True,
        }]

    @pytest.mark.parametrize('node, expected', (
        (Param.path('a'), '{a}'),
        (Param.path('a', Type.String), '{a}'),
    ))
    def test_swagger_node_formatter(self, node, expected):
        actual = swagger.SwaggerSpec.swagger_node_formatter(node)
        assert actual == expected

    def test_parse_operations(self):
        @Operation(path="a/{b:String}", methods=Method.POST, resource=User)
        def my_func(request, b):
            pass

        target = swagger.SwaggerSpec("Example", schemes='http')

        ApiInterfaceBase(
            ApiVersion(
                target,
                my_func,
            ),
        )

        actual = target.parse_operations()
        assert len(actual) == 2
        actual_paths, actual_resources = actual

        # Paths
        assert len(actual_paths) == 1
        assert "/a/{b}" in actual_paths
        actual_path = actual_paths['/a/{b}']
        assert actual_path['parameters'] == [{'in': 'path', 'type': 'string', 'name': 'b', 'required': True}]

        assert 'post' in actual_path
        actual_operation = actual_path['post']
        assert actual_operation == my_func.to_swagger()

        # Resources
        assert len(actual_resources) == 3
        assert 'tests.User' in actual_resources

    def test_get_swagger(self, monkeypatch):
        monkeypatch.setattr(swagger, 'CODECS', {
            'application/json': None  # Only the Keys are used.
        })

        request = MockRequest()
        target = swagger.SwaggerSpec("Example", schemes='http')

        base = ApiInterfaceBase(
            ApiVersion(
                target,
            ),
        )

        base.registered_codecs.clear()
        base.registered_codecs['application/yaml'] = None  # Only the keys are used.

        actual = target.get_swagger(request)
        expected = {
            'swagger': '2.0',
            'info': {
                'title': 'Example',
                'version': '1'
            },
            'host': '127.0.0.1',
            'schemes': ['http'],
            'basePath': '/api/v1',
            'consumes': ['application/yaml'],
            'produces': ['application/yaml'],
            'paths': {},
            'definitions': {
                'Error': {
                    'type': 'object',
                    'properties': {
                        'code': {
                            'description': 'Custom application specific error code that references into the application.',
                            'type': 'integer', 'format': 'int64',
                        },
                        'developer_message': {
                            'description': 'An error message suitable for the application developer',
                            'type': 'string'
                        },
                        'message': {
                            'description': 'A message that can be displayed to an end user',
                            'type': 'string'
                        },
                        'meta': {
                            'description': 'Additional meta information that can help solve errors.',
                        },
                        'status': {
                            'description': 'HTTP status code of the response.',
                            'type': 'integer', 'format': 'int64',
                        }
                    },
                },
                'Listing': {
                    'type': 'object',
                    'properties': {
                        'limit': {
                            'description': 'Limit or page size of the result set',
                            'type': 'integer', 'format': 'int64',
                        },
                        'offset': {
                            'description': 'Offset within the result set.',
                            'type': 'integer', 'format': 'int64',
                        },
                        'results': {
                            'description': 'List of resources.',
                        },
                        'total_count': {
                            'description': 'The total number of items in the result set.',
                            'type': 'integer', 'format': 'int64',
                        }
                    },
                }
            }
        }
        assert actual == expected

    def test_load_static(self):
        target = swagger.SwaggerSpec("", enable_ui=True)

        actual = target.load_static('ui.html')
        if _compat.PY2:
            assert actual.startswith('<!DOCTYPE html>')
        else:
            assert actual.startswith(b'<!DOCTYPE html>')

    def test_load_static__not_found_if_not_found(self):
        target = swagger.SwaggerSpec("")

        with pytest.raises(HttpError) as ex:
            target.load_static('eek.html')

        assert ex.value.status == HTTPStatus.NOT_FOUND

    def test_load_static__not_found_if_path_breakout_attempted(self):
        target = swagger.SwaggerSpec("")

        with pytest.raises(HttpError) as ex:
            target.load_static('/etc/passwd')

        assert ex.value.status == HTTPStatus.NOT_FOUND

    def test_get_ui(self):
        target = swagger.SwaggerSpec("")

        actual = target.get_ui(None)

        assert actual.body.startswith("<!DOCTYPE html>")
        assert actual.status == HTTPStatus.OK
        assert actual['Content-Type'] == 'text/html'

    @pytest.mark.parametrize('file_name, content_type', (
        ("ui.css", 'text/css'),
        ("bundle.js", 'application/javascript'),
    ))
    def test_get_static(self, file_name, content_type):
        target = swagger.SwaggerSpec("")

        actual = target.get_static(None, file_name)

        # Can't check the body as it is pre-gzipped
        assert actual.status == HTTPStatus.OK
        assert actual['Content-Type'] == content_type
        assert actual['Content-Encoding'] == 'gzip'

    def test_get_static__not_found_if_unknown_content_type(self):
        target = swagger.SwaggerSpec("")

        with pytest.raises(HttpError) as ex:
            target.get_static(None, 'ui.html')

        assert ex.value.status == HTTPStatus.NOT_FOUND
