# -*- coding: utf-8 -*-
import itertools
import os

from odin.utils import lazy_property

from odinweb import api

DATA_TYPE_MAP = {
    'int': api.TYPE_INTEGER,
    'float': api.TYPE_NUMBER,
    'str': api.TYPE_STRING,
    'bool': api.TYPE_BOOLEAN
}


class SwaggerSpec(api.ResourceApi):
    """
    Resource API instance that generates a Swagger spec of the current API.
    """
    api_name = 'swagger'

    def __init__(self, title, enable_ui=True):
        super(SwaggerSpec, self).__init__()
        self.title = title
        self.enable_ui = enable_ui

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
        return self.base_path + 'swagger'

    @staticmethod
    def generate_parameters(path):
        parameters = []
        for node in path:
            if isinstance(node, api.PathNode):
                parameters.append({
                    'name': node.name,
                    'in': api.IN_PATH,
                    'type': DATA_TYPE_MAP.get(node.type, api.TYPE_STRING),
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
            operation_spec = api.get_docs(api_route.callback)
            operation_spec.setdefault('operationId', api_route.callback.__name__)

            # Add methods
            for method in api_route.methods:
                path_spec[method.lower()] = operation_spec

        return paths

    @api.route
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
            'basePath': self.base_path,
            'info': {
                'title': self.title,
                'version': str(getattr(api_base, 'version', 0))
            },
            'paths': self.flatten_routes(api_base)
        }

    def serve_static(self, file_name):
        if not self.enable_ui:
            raise api.HttpError(404, 40401, "Not found")

        static_path = os.path.join(os.path.dirname(__file__), 'static')
        file_path = os.path.abspath(os.path.join(static_path, file_name))
        if not file_path.startswith(static_path):
            raise api.HttpError(404, 40401, "Not found")

        try:
            with open(file_path) as f:
                return api.HttpResponse(f.read(), headers={'content-type': 'text/html'})
        except:
            raise api.HttpError(404, 40401, "Not found")

    @api.route(sub_path=('ui',))
    def get_ui(self, request):
        return self.serve_static('ui.html')

    @api.route(sub_path=('ui', api.PathNode('file_name', 'string', None)))
    def get_static(self, request, file_name=None):
        return self.serve_static(file_name)
