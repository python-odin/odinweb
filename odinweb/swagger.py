# -*- coding: utf-8 -*-
import itertools
import os

from odin import fields
from odin.utils import getmeta, lazy_property

from odinweb import api, doc
from odinweb import resources
from odinweb._compat import *
from odinweb.constants import *
from odinweb.decorators import RouteDefinition

DATA_TYPE_MAP = {
    'int': Type.Integer,
    'float': Type.Number,
    'str': Type.String,
    'bool': Type.Boolean,
}
"""
Mapping between type names and swagger data types.
"""


SWAGGER_SPEC_TYPE_MAPPING = {
    fields.IntegerField: Type.Integer,
    fields.FloatField: Type.Number,
    fields.BooleanField: Type.Boolean,
}
"""
Mapping of fields to Swagger types.
"""

SWAGGER_SPEC_FORMAT_MAPPING = {
    fields.StringField: '',
    fields.IntegerField: 'int64',
    fields.FloatField: 'float',
    fields.BooleanField: '',
    fields.DateField: 'date',
    fields.DateTimeField: 'date-time',
    fields.NaiveTimeField: 'date-time',
}
"""
Mapping of fields to Swagger formats.
"""


def resource_definition(resource):
    """
    Generate a `Swagger Definitions Object <http://swagger.io/specification/#definitionsObject>`_
    from a resource.

    """
    meta = getmeta(resource)

    definition = {
        'type': "object",
        'properties': {}
    }

    for field in meta.all_fields:
        field_definition = {
            'type': SWAGGER_SPEC_TYPE_MAPPING.get(field.__class__, Type.String).value
        }

        if field in SWAGGER_SPEC_FORMAT_MAPPING:
            field_definition['format'] = SWAGGER_SPEC_FORMAT_MAPPING[field]

        if field.doc_text:
            field_definition['description'] = field.doc_text

        if field.choices:
            field_definition['enum'] = field.choices

        definition['properties'][field.name] = field_definition

    return definition


class SwaggerSpec(api.ResourceApi):
    """
    Resource API instance that generates a Swagger spec of the current API.
    """
    api_name = 'swagger'

    def __init__(self, title, enable_ui=False):
        super(SwaggerSpec, self).__init__()
        self.title = title
        self.enable_ui = enable_ui

        # Register UI routes
        if enable_ui:
            self._routes.append(RouteDefinition(
                0, api.PathType.Collection, ('GET',), ('ui',),
                SwaggerSpec.get_ui))
            self._routes.append(RouteDefinition(
                0, api.PathType.Collection, ('GET',), ('ui', api.PathNode('file_name', 'string', None)),
                SwaggerSpec.get_static))

        self._ui_cache = None

    @lazy_property
    def base_path(self):
        """
        Calculate the APIs base path
        """
        path = []

        # Walk up the API to find the base object
        parent = self.parent
        while parent:
            if parent.path_prefix:
                path.append(parent.path_prefix)
            parent = getattr(parent, 'parent', None)

        return '/' + '/'.join(itertools.chain.from_iterable(reversed(path)))

    @property
    def swagger_path(self):
        return self.base_path + '/swagger'

    @staticmethod
    def generate_parameters(path):
        parameters = []
        for node in path:
            if isinstance(node, api.PathNode):
                parameters.append({
                    'name': node.name,
                    'in': api.In.Path.value,
                    'type': DATA_TYPE_MAP.get(node.type, Type.String).value,
                    'required': True
                })
        return parameters

    def flatten_routes(self, api_base):
        """
        Flatten routes into a path -> method -> route structure
        """
        def parse_node(node):
            return "{{{}}}".format(node.name) if isinstance(node, api.PathNode) else str(node)

        paths = {}
        for api_route in api_base.api_routes(api_base.path_prefix[1:]):
            # We need to iterate this multiple times so convert to tuple
            api_route_path = tuple(api_route.path)

            # Add path spec object
            path = '/' + '/'.join(parse_node(p) for p in api_route_path)
            path_spec = paths.setdefault(path, {})

            # Add path parameters
            parameters = self.generate_parameters(api_route_path)
            if parameters:
                path_spec['parameters'] = parameters

            # Generate operation spec
            docs = doc.OperationDoc.get(api_route.callback)

            # Add methods
            for method in api_route.methods:
                path_spec[method.lower()] = docs.to_dict()

        return paths

    def resource_definitions(self, api_base):
        definitions = {
            getmeta(resources.Error).resource_name: resource_definition(resources.Error),
            getmeta(resources.Listing).resource_name: resource_definition(resources.Listing),
        }
        definitions.update({
            getmeta(resource).resource_name: resource_definition(resource)
            for resource in api_base.referenced_resources()
        })
        return definitions

    @api.route
    @doc.operation(tags=('swagger-ui',))
    @doc.response(200, "Swagger JSON of this API")
    def get_swagger(self, request):
        """
        Generate this document.
        """
        api_base = self.parent
        if not api_base:
            raise api.HttpError(404, 40442, "Swagger not available.",
                                "Swagger API is detached from a parent container.")

        return {
            'swagger': '2.0',
            'info': {
                'title': self.title,
                'version': str(getattr(api_base, 'version', 0))
            },
            'host': request.host,
            'basePath': self.base_path,
            'consumes': list(api.CODECS.keys()),
            'produces': list(api.CODECS.keys()),
            'paths': self.flatten_routes(api_base),
            'definitions': self.resource_definitions(api_base),
        }

    def load_static(self, file_name):
        if not self.enable_ui:
            raise api.HttpError(404, 40401, "Not found")

        static_path = os.path.join(os.path.dirname(__file__), 'static')
        file_path = os.path.abspath(os.path.join(static_path, file_name))
        if not file_path.startswith(static_path):
            raise api.HttpError(404, 40401, "Not found")

        try:
            return open(file_path, 'rb').read()
        except OSError:
            raise api.HttpError(404, 40401, "Not found")

    @doc.operation(tags=('swagger-ui',))
    @doc.response(200, "HTML content")
    @doc.produces('text/html')
    def get_ui(self, request):
        """
        Load the Swagger UI interface
        """
        if not self._ui_cache:
            content = self.load_static('ui.html')
            if isinstance(content, binary_type):
                content = content.decode('UTF-8')
            self._ui_cache = content.replace(u"{{SWAGGER_PATH}}", self.swagger_path)
        return api.HttpResponse(self._ui_cache, headers={'ContentType': 'text/html'})

    @doc.operation(tags=('swagger-ui',))
    @doc.response(200, "HTML content")
    def get_static(self, request, file_name=None):
        """
        Get static content for UI.
        """
        content_type = {
            'ss': 'text/css',
            'js': 'application/javascript',
        }.get(file_name[-2:])
        if not content_type:
            raise api.ImmediateHttpResponse("Not Found", 404)

        return api.HttpResponse(self.load_static(file_name), headers={
            'Content-Type': content_type,
            'Content-Encoding': 'gzip',
            'Cache-Control': 'public, max-age=300',
        })
