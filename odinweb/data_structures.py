from __future__ import absolute_import

import re

from collections import namedtuple
from odin.utils import getmeta, lazy_property, force_tuple

# Imports for typing support
from typing import Dict, Union, Optional, Callable, Any, AnyStr  # noqa
from odin import Resource  # noqa

from . import _compat
from .constants import HTTPStatus, In, Type
from .utils import dict_filter, sort_by_priority

__all__ = ('DefaultResource', 'HttpResponse', 'UrlPath', 'PathParam', 'NoPath', 'Param', 'Response')


class DefaultResource(object):
    """
    A helper object that indicates that the default resource should be used.

    The default resource is then obtained from the bound object.

    """
    def __new__(cls):
        return DefaultResource


class HttpResponse(object):
    """
    Simplified HTTP response
    """
    __slots__ = ('status', 'body', 'headers')

    @classmethod
    def from_status(cls, http_status, headers=None):
        # type: (HTTPStatus, Dict[str]) -> HttpResponse
        return cls(http_status.description or http_status.phrase, http_status, headers)

    def __init__(self, body, status=HTTPStatus.OK, headers=None):
        # type: (Any, HTTPStatus, Dict[str, AnyStr]) -> None
        self.body = body
        if isinstance(status, HTTPStatus):
            status = status.value
        self.status = status
        self.headers = headers or {}

    def __getitem__(self, item):
        # type: (str) -> AnyStr
        return self.headers[item]

    def __setitem__(self, key, value):
        # type: (str, AnyStr) -> None
        self.headers[key] = value

    def set_content_type(self, value):
        # type: (AnyStr) -> None
        """
        Set Response content type.
        """
        self.headers['Content-Type'] = value


# Used to define path nodes
PathParam = namedtuple('PathParam', 'name type type_args')
PathParam.__new__.__defaults__ = (None, Type.Integer, None)


def _add_nodes(a, b):
    if b and b[0] == '':
        raise ValueError("Right hand argument cannot be absolute.")
    return a + b


def _to_swagger(base=None, description=None, resource=None, options=None):
    # type: (Dict[str, str], str, Resource, Dict[str, str]) -> Dict[str, str]
    """
    Common to swagger definition.

    :param base: The base dict.
    :param description: An optional description.
    :param resource: An optional resource.
    :param options: Any additional options

    """
    definition = dict_filter(base or {}, options or {})

    if description:
        definition['description'] = description.format(
            name=getmeta(resource).name if resource else "UNKNOWN"
        )

    if resource:
        definition['schema'] = {
            '$ref': '#/definitions/{}'.format(getmeta(resource).resource_name)
        }

    return definition


PATH_NODE_RE = re.compile(r'^{([\w_]+)(?::([\w_]+))?}$')


class UrlPath(object):
    """
    Object that represents a URL path.
    """
    __slots__ = ('_nodes',)

    @classmethod
    def from_object(cls, obj):
        # type: (Any) -> UrlPath
        """
        Attempt to convert any object into a UrlPath.

        Raise a value error if this is not possible.
        """
        if isinstance(obj, UrlPath):
            return obj
        if isinstance(obj, _compat.string_types):
            return UrlPath.parse(obj)
        if isinstance(obj, PathParam):
            return UrlPath(obj)
        if isinstance(obj, (tuple, list)):
            return UrlPath(*obj)
        raise ValueError("Unable to convert object to UrlPath `%r`" % obj)

    @classmethod
    def parse(cls, url_path):
        # type: (str) -> UrlPath
        """
        Parse a string into a URL path (simple eg does not support typing of URL parameters)
        """
        if not url_path:
            return cls()

        nodes = []
        for node in url_path.rstrip('/').split('/'):
            # Identifies a PathNode
            if '{' in node or '}' in node:
                m = PATH_NODE_RE.match(node)
                if not m:
                    raise ValueError("Invalid path param: {}".format(node))

                # Parse out name and type
                name = m.group(1)
                param_type = m.group(2)
                if param_type:
                    try:
                        path_param = PathParam(name, Type[param_type])
                    except KeyError:
                        raise ValueError("Unknown param type `{}` in: {}".format(param_type, node))
                else:
                    path_param = PathParam(name)

                nodes.append(path_param)
            else:
                nodes.append(node)

        return cls(*nodes)

    def __init__(self, *nodes):
        # type: (*Union(str, PathParam)) -> None
        self._nodes = nodes

    def __hash__(self):
        return hash(str(self))

    def __str__(self):
        return self.format()

    def __repr__(self):
        return "{}({})".format(
            self.__class__.__name__,
            ', '.join(repr(n) for n in self._nodes)
        )

    def __add__(self, other):
        # type: (Union[UrlPath, str, PathParam]) -> UrlPath
        if isinstance(other, UrlPath):
            return UrlPath(*_add_nodes(self._nodes, other._nodes))  # pylint:disable=protected-access
        if isinstance(other, _compat.string_types):
            return self + UrlPath.parse(other)
        if isinstance(other, PathParam):
            return UrlPath(*_add_nodes(self._nodes, (other,)))
        return NotImplemented

    def __radd__(self, other):
        # type: (Union[str, PathParam]) -> UrlPath
        if isinstance(other, _compat.string_types):
            return UrlPath.parse(other) + self
        if isinstance(other, PathParam):
            return UrlPath(*_add_nodes((other,), self._nodes))
        return NotImplemented

    def __eq__(self, other):
        # type: (UrlPath) -> bool
        if isinstance(other, UrlPath):
            return self._nodes == other._nodes  # pylint:disable=protected-access
        return NotImplemented

    def __getitem__(self, item):
        # type: (Union[int, slice]) -> UrlPath
        return UrlPath(*force_tuple(self._nodes[item]))

    @property
    def is_absolute(self):
        # type: () -> bool
        """
        Is an absolute URL
        """
        return len(self._nodes) and self._nodes[0] == ''

    @property
    def path_nodes(self):
        """
        Return iterator of PathNode items
        """
        return (n for n in self._nodes if isinstance(n, PathParam))

    @staticmethod
    def odinweb_node_formatter(path_node):
        # type: (PathParam) -> str
        """
        Format a node to be consumable by the `UrlPath.parse`.
        """
        if path_node.type:
            return "{{{}:{}}}".format(path_node.name, path_node.type.name)
        return "{{{}}}".format(path_node.name)

    def format(self, node_formatter=None):
        # type: (Optional[Callable[[PathParam], str]]) -> str
        """
        Format a URL path.
        
        An optional `node_parser(PathNode)` can be supplied for converting a 
        `PathNode` into a string to support the current web framework.  
        
        """
        if self._nodes == ('',):
            return '/'
        else:
            node_formatter = node_formatter or self.odinweb_node_formatter
            return '/'.join(node_formatter(n) if isinstance(n, PathParam) else n for n in self._nodes)

NoPath = UrlPath()


class Param(object):
    """
    Represents a generic parameter object.
    """
    __slots__ = ('name', 'in_', 'type', 'resource', 'description', 'options')

    @classmethod
    def path(cls, name, type_=Type.String, description=None, default=None,
             minimum=None, maximum=None, enum=None, **options):
        """
        Define a path parameter
        """
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValueError("Minimum must be less than or equal to the maximum.")
        return cls(name, In.Path, type_, None, description,
                   default=default, minimum=minimum, maximum=maximum,
                   enum=enum, required=True, **options)

    @classmethod
    def query(cls, name, type_=Type.String, description=None, required=None, default=None,
              minimum=None, maximum=None, enum=None, **options):
        """
        Define a query parameter
        """
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValueError("Minimum must be less than or equal to the maximum.")
        return cls(name, In.Query, type_, None, description,
                   required=required, default=default,
                   minimum=minimum, maximum=maximum,
                   enum=enum, **options)

    @classmethod
    def header(cls, name, type_=Type.String, description=None, default=None, required=None, **options):
        """
        Define a header parameter.
        """
        return cls(name, In.Header, type_, None, description,
                   required=required, default=default,
                   **options)

    @classmethod
    def body(cls, description=None, default=None, resource=DefaultResource, **options):
        """
        Define body parameter.
        """
        return cls('body', In.Body, None, resource, description, required=True,
                   default=default, **options)

    @classmethod
    def form(cls, name, type_=Type.String, description=None, required=None, default=None,
             minimum=None, maximum=None, enum=None, **options):
        """
        Define form parameter.
        """
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValueError("Minimum must be less than or equal to the maximum.")
        return cls(name, In.Form, type_, None, description,
                   required=required, default=default,
                   minimum=minimum, maximum=maximum,
                   enum=enum, **options)

    def __init__(self, name, in_, type_=None, resource=None, description=None, **options):
        # type: (str, In, Optional[Type], Optional(Resource), Optional(str), **Any) -> None
        self.name = name
        self.in_ = in_
        self.type = type_
        self.resource = resource
        self.description = description
        self.options = dict_filter(**options)

    def __hash__(self):
        return hash(self.in_.value + ':' + self.name)

    def __str__(self):
        return "{} param {}".format(self.in_.value.title(), self.name)

    def __repr__(self):
        return "Param({!r}, {!r}, {!r}, {!r}, {!r})".format(self.name, self.in_, self.type, self.resource, self.options)

    def __eq__(self, other):
        if isinstance(other, Param):
            return hash(self) == hash(other)
        return NotImplemented

    def to_swagger(self, bound_resource=None):
        """
        Generate a swagger representation.
        """
        return _to_swagger(
            {
                'name': self.name,
                'in': self.in_.value,
                'type': self.type.value if self.type else None,
            },
            description=self.description,
            resource=bound_resource if self.resource is DefaultResource else self.resource,
            options=self.options
        )


class Response(object):
    """
    Definition of a swagger response.
    """
    __slots__ = ('status', 'description', 'resource')

    def __init__(self, status, description=None, resource=DefaultResource):
        # type: (HTTPStatus, str, Optional(Resource)) -> None
        self.status = status
        self.description = description
        self.resource = resource

    def __hash__(self):
        return hash(self.status)

    def __str__(self):
        description = self.description or self.status.description
        if description:
            return "{} {} - {}".format(self.status.value, self.status.phrase, description)
        else:
            return "{} {}".format(self.status.value, self.status.phrase)

    def __repr__(self):
        return "Response({!r}, {!r}, {!r})".format(self.status, self.description, self.resource)

    def __eq__(self, other):
        if isinstance(other, Response):
            return hash(self) == hash(other)
        return NotImplemented

    def to_swagger(self, bound_resource=None):
        """
        Generate a swagger representation.
        """
        response_def = _to_swagger(
            description=self.description,
            resource=bound_resource if self.resource is DefaultResource else self.resource,
        )
        status = self.status if self.status == 'default' else self.status.value
        return status, response_def


class DefaultResponse(Response):
    """
    Default response object
    """
    def __init__(self, description, resource=DefaultResource):
        # type: (str, Optional(Resource)) -> None
        super(DefaultResponse, self).__init__('default', description, resource)


class MiddlewareList(list):
    """
    List of middleware with filtering and sorting builtin.
    """
    @lazy_property
    def pre_dispatch(self):
        """
        List of pre-dispatch methods from registered middleware.
        """
        middleware = sort_by_priority(self)
        return tuple(m.pre_dispatch for m in middleware if hasattr(m, 'pre_dispatch'))

    @lazy_property
    def post_dispatch(self):
        """
        List of post-dispatch methods from registered middleware.
        """
        middleware = sort_by_priority(self, reverse=True)
        return tuple(m.post_dispatch for m in middleware if hasattr(m, 'post_dispatch'))

    @lazy_property
    def post_swagger(self):
        """
        List of post-swagger methods from registered middleware.

        This is used to modify documentation (eg add/remove any extra information, provided by the middleware)

        """
        middleware = sort_by_priority(self)
        return tuple(m.post_swagger for m in middleware if hasattr(m, 'post_swagger'))
