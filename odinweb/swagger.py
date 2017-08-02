# -*- coding: utf-8 -*-
"""
Swagger Support
~~~~~~~~~~~~~~~

Built in support for generating a swagger spec, along with built in Swagger UI.

To enable add the :py:class:`SwaggerSpec` resource API into your API::

    >>> from odinweb import api
    >>> from odinweb.swagger import SwaggerSpec
    >>> my_api = api.ApiCollection(
    ...    SwaggerSpec("Title of my Swagger spec", enable_ui=True),
    ... )

"""
import collections
import os

from typing import List, Dict, Any, Union, Tuple  # noqa

from odin import fields
from odin.utils import getmeta, lazy_property, force_tuple

from . import doc
from . import resources
from ._compat import binary_type
from .constants import HTTPStatus, Type
from .containers import ResourceApi, CODECS
from .data_structures import PathParam, UrlPath, Param, HttpResponse, NoPath
from .decorators import Operation
from .exceptions import HttpError
from .utils import dict_filter


SWAGGER_SPEC_TYPE_MAPPING = {t.odin_field: t for t in Type}
"""
Mapping of fields to Swagger types.
"""

SWAGGER_SPEC_FORMAT_MAPPING = {
    fields.IntegerField: 'int64',
    fields.FloatField: 'float',
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

        if field.__class__ in SWAGGER_SPEC_FORMAT_MAPPING:
            field_definition['format'] = SWAGGER_SPEC_FORMAT_MAPPING[field.__class__]

        if field.doc_text:
            field_definition['description'] = field.doc_text

        if field.choices:
            field_definition['enum'] = [c[0] for c in field.choices]

        definition['properties'][field.name] = field_definition

    return definition


class SwaggerSpec(ResourceApi):
    """
    Resource API instance that generates a Swagger spec of the current API.
    """
    api_name = 'swagger'
    SWAGGER_TAG = 'swagger'
    tags = (SWAGGER_TAG, )

    static_path = os.path.join(os.path.dirname(__file__), 'static')

    def __init__(self, title, enabled=True, enable_ui=False, host=None, schemes=None):
        # type: (str, bool, bool, str, Union[str, Tuple[str]]) -> None
        # Register operations
        if enabled:
            self._operations.append(Operation(SwaggerSpec.get_swagger)
)
            if enable_ui:
                self._operations.append(Operation(SwaggerSpec.get_ui, UrlPath.parse('ui')))
                self._operations.append(Operation(SwaggerSpec.get_static, UrlPath.parse('ui/{file_name:String}')))

        super(SwaggerSpec, self).__init__()
        self.title = title
        self.enabled = enabled
        self.enable_ui = enabled and enable_ui
        self.host = host
        self.schemes = set(force_tuple(schemes or ()))

        self._ui_cache = None

    @lazy_property
    def base_path(self):
        """
        Calculate the APIs base path
        """
        path = UrlPath()

        # Walk up the API to find the base object
        parent = self.parent
        while parent:
            path_prefix = getattr(parent, 'path_prefix', NoPath)
            path = path_prefix + path
            parent = getattr(parent, 'parent', None)

        return path

    @property
    def swagger_path(self):
        return self.base_path + 'swagger'

    @staticmethod
    def generate_parameters(path):
        # type: (UrlPath) -> List[Dict[str, Any]]
        return [Param.path(node.name, node.type).to_swagger() for node in path.path_nodes]

    @staticmethod
    def swagger_node_formatter(path_node):
        # type: (PathParam) -> str
        """
        Format a node for swagger spec (default formatter for the format method).
        """
        return "{{{}}}".format(path_node.name)

    def parse_operations(self):
        """
        Flatten routes into a path -> method -> route structure
        """
        resource_defs = {
            getmeta(resources.Error).resource_name: resource_definition(resources.Error),
            getmeta(resources.Listing).resource_name: resource_definition(resources.Listing),
        }

        paths = collections.OrderedDict()
        for path, operation in self.parent.op_paths():
            # Cut of first item (will be the parents path)
            path = '/' + path[1:]  # type: UrlPath

            # Filter out swagger endpoints
            if self.SWAGGER_TAG in operation.tags:
                continue

            # Add to resource definitions
            if operation.resource:
                resource_defs[getmeta(operation.resource).resource_name] = resource_definition(operation.resource)

            # Add path parameters
            path_spec = paths.setdefault(path.format(self.swagger_node_formatter), {})

            # Add parameters
            parameters = self.generate_parameters(path)
            if parameters:
                path_spec['parameters'] = parameters

            # Add methods
            for method in operation.methods:
                path_spec[method.value.lower()] = operation.to_swagger()

        return paths, resource_defs

    @doc.response(HTTPStatus.OK, "Swagger JSON of this API")
    def get_swagger(self, request):
        """
        Generate this document.
        """
        api_base = self.parent
        paths, definitions = self.parse_operations()
        return dict_filter({
            'swagger': '2.0',
            'info': {
                'title': self.title,
                'version': str(getattr(api_base, 'version', 0))
            },
            'host': self.host or request.host,
            'schemes': list(self.schemes) or None,
            'basePath': str(self.base_path),
            'consumes': list(CODECS.keys()),
            'produces': list(CODECS.keys()),
            'paths': paths,
            'definitions': definitions,
        })

    def load_static(self, file_name):
        file_path = os.path.abspath(os.path.join(self.static_path, file_name))
        # This is a security check to ensure this is not abused to
        # read files outside of the static folder.
        if not file_path.startswith(self.static_path):
            raise HttpError(HTTPStatus.NOT_FOUND, 42)

        try:
            return open(file_path, 'rb').read()
        except IOError:
            raise HttpError(HTTPStatus.NOT_FOUND, 42)

    @doc.response(HTTPStatus.OK, "HTML content")
    @doc.produces('text/html')
    def get_ui(self, _):
        """
        Load the Swagger UI interface
        """
        if not self._ui_cache:
            content = self.load_static('ui.html')
            if isinstance(content, binary_type):
                content = content.decode('UTF-8')
            self._ui_cache = content.replace(u"{{SWAGGER_PATH}}", str(self.swagger_path))
        return HttpResponse(self._ui_cache, headers={
            'Content-Type': 'text/html'
        })

    @doc.response(HTTPStatus.OK, "HTML content")
    def get_static(self, _, file_name=None):
        """
        Get static content for UI.
        """
        content_type = {
            'ss': 'text/css',
            'js': 'application/javascript',
        }.get(file_name[-2:])
        if not content_type:
            raise HttpError(HTTPStatus.NOT_FOUND, 42)

        return HttpResponse(self.load_static(file_name), headers={
            'Content-Type': content_type,
            'Content-Encoding': 'gzip',
            'Cache-Control': 'public, max-age=300',
        })
