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

# Imported for typing support
from typing import List, Dict, Any, Union, Tuple  # noqa

from odin.fields.virtual import VirtualField
from .data_structures import PathParam  # noqa

from odin import fields
from odin.utils import getmeta, lazy_property, force_tuple

from . import doc
from . import resources
from ._compat import binary_type
from .constants import HTTPStatus, Type
from .containers import ResourceApi, CODECS
from .data_structures import UrlPath, Param, HttpResponse, NoPath, DefaultResource
from .decorators import Operation
from .exceptions import HttpError
from .utils import dict_filter


SWAGGER_SPEC_TYPE_MAPPING = [
    (fields.IntegerField, Type.Long),
    (fields.FloatField, Type.Float),
    (fields.EmailField, Type.Email),
    (fields.StringField, Type.String),
    (fields.TimeField, Type.Time),
    (fields.DateField, Type.Date),
    (fields.DateTimeField, Type.DateTime),
    (fields.BooleanField, Type.Boolean),
]
"""
Mapping of fields to Swagger types.
"""


def map_field_to_type(field):
    # type: (Any) -> Type
    for field_type, type_ in SWAGGER_SPEC_TYPE_MAPPING:
        if isinstance(field, field_type):
            return type_


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
        field_definition = {}

        type_def = map_field_to_type(field)
        if type_def:
            field_definition['type'] = str(type_def)
            if type_def.format:
                field_definition['format'] = type_def.format

        if field.doc_text:
            field_definition['description'] = field.doc_text

        if isinstance(field, VirtualField) or field in meta.readonly_fields:
            field_definition['readOnly'] = True

        # Use getattr to support calculated fields
        if getattr(field, 'choices', None):
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
            self._operations.append(Operation(SwaggerSpec.get_swagger))
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
    def cenancestor(self):
        """
        Last universal ancestor (or the top level of the API structure).
        """
        ancestor = parent = self.parent
        while parent:
            ancestor = parent
            parent = getattr(parent, 'parent', None)
        return ancestor

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

    def security_definitions(self):
        """
        Chance to generate security definitions.
        """
        return None

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

            # Add any resource definitions from responses
            if operation.responses:
                for response in operation.responses:
                    resource = response.resource
                    # Ensure we have a resource
                    if resource and resource is not DefaultResource:
                        resource_name = getmeta(resource).resource_name
                        # Don't generate a resource definition if one has already been created.
                        if resource_name not in resource_defs:
                            resource_defs[resource_name] = resource_definition(resource)

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
        codecs = getattr(self.cenancestor, 'registered_codecs', CODECS)  # type: dict
        return dict_filter({
            'swagger': '2.0',
            'info': {
                'title': self.title,
                'version': str(getattr(api_base, 'version', 0))
            },
            'host': self.host or request.host,
            'schemes': list(self.schemes) or None,
            'basePath': str(self.base_path),
            'consumes': list(codecs.keys()),
            'produces': list(codecs.keys()),
            'paths': paths,
            'definitions': definitions,
            'securityDefinitions': self.security_definitions(),
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
