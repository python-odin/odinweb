from collections import namedtuple
from typing import Dict, Union, List, Optional, Callable, Any

from . import _compat
from .constants import *

# Generic definition for a route to an API endpoint
ApiRoute = namedtuple("ApiRoute", 'path methods operation')


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
        self.body = body
        if isinstance(status, HTTPStatus):
            status = status.value
        self.status = status
        self.headers = headers or {}

    def __getitem__(self, item):
        return self.headers[item]

    def __setitem__(self, key, value):
        self.headers[key] = value

    def set_content_type(self, value):
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
            return UrlPath(*obj._nodes)  # "Copy" object
        if isinstance(obj, _compat.text_type):
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
        if isinstance(other, str):
            return self + UrlPath.parse(other)
        if isinstance(other, PathNode):
            return UrlPath(*_add_nodes(self._nodes, (other,)))
        return NotImplemented

    def __radd__(self, other):
        # type: (Union[str, PathNode]) -> UrlPath
        if isinstance(other, str):
            return UrlPath.parse(other) + self
        if isinstance(other, PathNode):
            return UrlPath(*_add_nodes((other,), self._nodes))
        return NotImplemented

    def __eq__(self, other):
        # type: (UrlPath) -> bool
        if isinstance(other, UrlPath):
            return self._nodes == other._nodes
        return NotImplemented

    @property
    def is_absolute(self):
        # type: () -> bool
        """
        Is an absolute URL
        """
        return len(self._nodes) and self._nodes[0] == ''

    @staticmethod
    def swagger_node_formatter(path_node):
        # type: (PathNode) -> str
        """
        Format a node for swagger spec (default formatter for the format method).
        """
        return "{{{}}}".format(path_node.name)

    @staticmethod
    def odinweb_node_formatter(path_node):
        # type: (PathNode) -> str
        """
        Format a node to be consumable by the `UrlPath.parse`.
        """
        if path_node.type:
            return "{{{}:{}}}".format(path_node.name, path_node.type.value)
        return "{{{}}}".format(path_node.name)

    def format(self, node_formatter=None):
        # type: (Optional[Callable[[PathNode], str]]) -> str
        """
        Format a URL path.
        
        An optional `node_parser(PathNode)` can be supplied for converting a 
        `PathNode` into a string to support the current web framework.  
        
        """
        node_formatter = node_formatter or self.odinweb_node_formatter
        return '/'.join(node_formatter(n) if isinstance(n, PathNode) else n for n in self._nodes)
