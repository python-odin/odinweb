from collections import namedtuple
from typing import Dict, Union, Optional, Callable, Any, AnyStr  # noqa

from odin.utils import getmeta

from . import _compat
from .constants import HTTPStatus, In, Type
from .utils import dict_filter


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
        self.headers['content-type'] = value


# Used to define path nodes
PathNode = namedtuple('PathNode', 'name type type_args')
PathNode.__new__.__defaults__ = (None, Type.Integer, None)


def _add_nodes(a, b):
    if b and b[0] == '':
        raise ValueError("Right hand argument cannot be absolute.")
    return a + b


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
        if isinstance(obj, PathNode):
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
        return cls(*url_path.rstrip('/').split('/')) if url_path else cls()

    def __init__(self, *nodes):
        # type: (*Union(str, PathNode)) -> None
        self._nodes = nodes

    def __str__(self):
        return self.format()

    def __repr__(self):
        return "{}({})".format(
            self.__class__.__name__,
            ', '.join(repr(n) for n in self._nodes)
        )

    def __add__(self, other):
        # type: (Union[UrlPath, str, PathNode]) -> UrlPath
        if isinstance(other, UrlPath):
            return UrlPath(*_add_nodes(self._nodes, other._nodes))
        if isinstance(other, _compat.string_types):
            return self + UrlPath.parse(other)
        if isinstance(other, PathNode):
            return UrlPath(*_add_nodes(self._nodes, (other,)))
        return NotImplemented

    def __radd__(self, other):
        # type: (Union[str, PathNode]) -> UrlPath
        if isinstance(other, _compat.string_types):
            return UrlPath.parse(other) + self
        if isinstance(other, PathNode):
            return UrlPath(*_add_nodes((other,), self._nodes))
        return NotImplemented

    def __eq__(self, other):
        # type: (UrlPath) -> bool
        if isinstance(other, UrlPath):
            return self._nodes == other._nodes
        return NotImplemented

    def __getitem__(self, item):
        # type: (Union[int, slice]) -> UrlPath
        return UrlPath(*self._nodes[item])

    @property
    def is_absolute(self):
        # type: () -> bool
        """
        Is an absolute URL
        """
        return len(self._nodes) and self._nodes[0] == ''

    @staticmethod
    def odinweb_node_formatter(path_node):
        # type: (PathNode) -> str
        """
        Format a node to be consumable by the `UrlPath.parse`.
        """
        if path_node.type:
            return "{{{}:{}}}".format(path_node.name, path_node.type.value)
        return "{{{}}}".format(path_node.name)

    @property
    def nodes(self):
        """
        Return iterator of PathNode items
        """
        return (n for n in self._nodes if isinstance(n, PathNode))

    def format(self, node_formatter=None):
        # type: (Optional[Callable[[PathNode], str]]) -> str
        """
        Format a URL path.
        
        An optional `node_parser(PathNode)` can be supplied for converting a 
        `PathNode` into a string to support the current web framework.  
        
        """
        node_formatter = node_formatter or self.odinweb_node_formatter
        return '/'.join(node_formatter(n) if isinstance(n, PathNode) else n for n in self._nodes)

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
        return cls(name, In.Path, type_, None, description,
                   default=default, minimum=minimum, maximum=maximum,
                   enum=enum, **options)

    @classmethod
    def query(cls, name, type_=Type.String, description=None, required=False, default=None,
              minimum=None, maximum=None, enum=None, **options):
        """
        Define a query parameter
        """
        return cls(name, In.Query, type_, None, description,
                   required=required, default=default,
                   minimum=minimum, maximum=maximum,
                   enum=enum, **options)

    @classmethod
    def header(cls, name, type_=Type.String, description=None, default=None, required=False, **options):
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
        return cls('body', In.Body, None, resource, description,
                   default=default, **options)

    @classmethod
    def form(cls, name, type_=Type.String, description=None, required=False, default=None,
             minimum=None, maximum=None, enum=None, **options):
        """
        Define form parameter.
        """
        return cls(name, In.Form, type_, None, description,
                   required=required, default=default,
                   minimum=minimum, maximum=maximum,
                   enum=enum, **options)

    def __init__(self, name, in_, type_=None, resource=None, description=None, **options):
        # type: (str, In, Optional[Type] **Dict[str, Any]) -> None
        self.name = name
        self.in_ = in_
        self.type = type_
        self.resource = resource
        self.description = description
        self.options = dict_filter(**options)

    def __hash__(self):
        return hash(self.in_.value + self.name)

    def __str__(self):
        return "{} - {}".format(self.in_.value, self.name)

    def __repr__(self):
        return "Param({!r}, {!r}, {!r}, {!r}, {!r})".format(self.name, self.in_, self.type, self.resource, self.options)

    def to_swagger(self, bound_resource=None):
        """
        Generate a swagger representation.
        """
        resource = bound_resource if self.resource is DefaultResource else self.resource

        param_def = dict_filter({
            'name': self.name,
            'in': self.in_.value,
            'type': self.type.value if self.type else None,
        }, self.options)

        if self.description:
            param_def['description'] = self.description.format(
                name=getmeta(resource).name if resource else "UNKNOWN"
            )

        if resource:
            param_def['schema'] = {
                '$ref': '#/definitions/{}'.format(getmeta(resource).resource_name)
            }

        return param_def
