"""
Decorators
~~~~~~~~~~

A collection of decorators for identifying the various types of route.

"""
from __future__ import absolute_import

from typing import Callable, Union, Tuple, Type
from collections import namedtuple
from functools import wraps

from odin import Resource
from odin.utils import force_tuple, lazy_property

from odinweb.utils import to_bool
from odinweb.data_structures import PathNode
from . import _compat
from .doc import OperationDoc
from .constants import *
from .resources import Listing

__all__ = (
    'Operation',
    # Basic routes
    'route', 'collection', 'collection_action', 'resource_route', 'resource_action',
    # Handlers
    'list_response', 'resource_request',
    # Shortcuts
    'listing', 'create', 'detail', 'update', 'patch', 'delete', 'action', 'detail_action',
)

# Counter used to order routes
_route_count = 0

# Definition of a route bound to a class method
RouteDefinition = namedtuple("RouteDefinition", 'route_number path_type methods sub_path callback')


class Operation(object):
    """
    Decorator for defining an API operation. Usually one of the helpers (listing, detail, update, delete) would be
    used in place of this route decorator.

    Usage::

        class ItemApi(ResourceApi):
            resource = Item

            @route(path=PathType.Collection, methods=Method.GET)
            def list_items(self, request):
                ...
                return items

    """
    _operation_count = 0

    @classmethod
    def decorate(cls, func=None, path_type=PathType.Collection, method=Method.GET, resource=None, sub_path=None):
        # type: (Callable, PathType, Union(Method, Tuple(Union)), Type[Resource], Union[Union(str, PathNode), Tuple(Union(str, PathNode))]) -> Operation
        """
        :param func: Function we are routing
        :param sub_path: A sub path that can be used as a action.
        :param path_type: Type of path, list/detail or custom.
        :param methods: HTTP method(s) this function responses to.
        :type methods: str | tuple(str) | list(str)
        :param resource: Specify the resource that this function encodes/decodes,
            default is the one specified on the ResourceAPI instance.
        """
        def wrapper(f):
            return cls(f, path_type, method, resource, sub_path)
        return wrapper(func) if func else wrapper

    def __init__(self, callback, path_type, method, resource, sub_path):
        # type: (Callable, PathType, Union(Method, Tuple(Union)), Type[Resource], Union[Union(str, PathNode), Tuple(Union(str, PathNode))]) -> None
        self.callback = callback
        self.path_type = path_type
        self.methods = force_tuple(method)
        self.resource = resource
        self.sub_path = force_tuple(sub_path)

        self._hash_id = Operation._operation_count
        Operation._operation_count += 1

        self.resource_api = None

    def __hash__(self):
        return self._hash_id

    def __call__(self, *args, **kwargs):
        return self.callback(*args, **kwargs)

    @property
    def is_bound(self):
        # type: () -> bool
        """
        Operation is bound to a resource api
        """
        return self.resource_api is not None

    @lazy_property
    def operation_id(self):
        return self.callback.__name__

    @lazy_property
    def path(self):
        resource_api = self.resource_api

        path = list(resource_api.path_prefix) + [resource_api.api_name]

        if self.path_type == PathType.Resource:
            path.append(PathNode(resource_api.resource_id_name, resource_api.resource_id_type, None))

        return path + list(self.sub_path or [])

    def bind_to_instance(self, instance):
        self.resource_api = instance


collection = collection_action = action = route = Operation.decorate


def resource_route(func=None, method=Method.GET, resource=None, sub_path=None):
    return Operation.decorate(func, PathType.Resource, method, resource, sub_path)

resource_action = detail_action = resource_route


# Handlers

def list_response(func=None, max_offset=None, default_offset=0, max_limit=None, default_limit=50):
    """
    Handle processing a list. It is assumed decorator will operate on a class method.

    This decorator extracts offer/limit values from the query string and returns
    a Listing response and applies total counts.

    """
    def inner(f):
        docs = OperationDoc.bind(f)
        docs.query_param('offset', Type.Integer, "Offset of first value", False, default_offset, 0, max_offset)
        docs.query_param('limit', Type.Integer, "Number of returned values", False, default_limit, 1, max_limit)
        docs.query_param('bare', Type.Boolean, "Return without list container", False, False)
        docs.add_response(HTTPStatus.OK, 'OK', Listing)

        @wraps(f)
        def wrapper(self, request, *args, **kwargs):
            # Get paging args from query string
            offset = int(request.GET.get('offset', default_offset))
            if offset < 0:
                offset = 0
            elif max_offset and offset > max_offset:
                offset = max_offset
            kwargs['offset'] = offset

            limit = int(request.GET.get('limit', default_limit))
            if limit < 1:
                limit = 1
            elif max_limit and limit > max_limit:
                limit = max_limit
            kwargs['limit'] = limit

            bare = to_bool(request.GET.get('bare', False))
            result = f(self, request, *args, **kwargs)
            if result is not None:
                if isinstance(result, tuple) and len(result) == 2:
                    result, total_count = result
                else:
                    total_count = None

                return result if bare else Listing(result, limit, offset, total_count)
        return wrapper

    return inner(func) if func else inner


def resource_request(func=None):
    """
    Handle processing a request with a resource body. 
    
    It is assumed decorator will operate on a class method.
    """
    def inner(f):
        OperationDoc.bind(f).body_param()

        @wraps(f)
        def wrapper(self, request, *args, **kwargs):
            item = self.get_resource(request, resource=f.resource)
            return f(self, request, item, *args, **kwargs)

        return wrapper

    return inner(func) if func else inner


# Shortcut methods

def listing(f=None, resource=Listing, max_offset=None, default_offset=0, max_limit=None, default_limit=50):
    """
    Decorator to indicate a listing endpoint.

    Usage::

        class ItemApi(ResourceApi):
            resource = Item

            @listing(path=PathType.Collection, methods=Method.Get)
            def list_items(self, request, offset, limit):
                ...
                return items

    :param f: Function we are routing
    :param resource: Specify the resource that this function
        encodes/decodes, default is the one specified on the ResourceAPI
        instance.
    :param default_offset: Default value for the offset from the start of listing.
    :param default_limit: Default value for limiting the response size.

    """
    def inner(func):
        return route(
            list_response(func, max_offset, default_offset, max_limit, default_limit),
            PathType.Collection, Method.GET, resource
        )
    return inner(f) if f else inner


def create(f=None, resource=None):
    """
    Decorator to indicate a creation endpoint.

    :param f: Function we are routing
    :param resource: Specify the resource that this function
        encodes/decodes, default is the one specified on the ResourceAPI
        instance.

    """
    def inner(func):
        OperationDoc.bind(func).add_response(HTTPStatus.CREATED, "Resource has been created", resource)
        return route(resource_request(func), PathType.Collection, Method.POST, resource)
    return inner(f) if f else inner


def detail(f=None, resource=None):
    """
    Decorator to indicate a detail endpoint.

    :param f: Function we are routing
    :param resource: Specify the resource that this function
        encodes/decodes, default is the one specified on the ResourceAPI
        instance.

    """
    def inner(func):
        OperationDoc.bind(func).add_response(HTTPStatus.OK, "Get a resource", resource)
        return route(func, PathType.Resource, Method.GET, resource)
    return inner(f) if f else inner


def update(f=None, resource=None):
    """
    Decorator to indicate an update endpoint.

    :param f: Function we are routing
    :param resource: Specify the resource that this function
        encodes/decodes, default is the one specified on the ResourceAPI
        instance.

    """
    def inner(func):
        OperationDoc.bind(func).add_response(HTTPStatus.OK, "Resource has been updated.", resource)
        return route(resource_request(func), PathType.Resource, Method.PUT, resource)
    return inner(f) if f else inner


def patch(f=None, resource=None):
    """
    Decorator to indicate a patch endpoint.

    :param f: Function we are routing
    :param resource: Specify the resource that this function
        encodes/decodes, default is the one specified on the ResourceAPI
        instance.

    """
    def inner(func):
        OperationDoc.bind(func).add_response(HTTPStatus.OK, "Resource has been patched.", resource)
        return route(resource_request(func), PathType.Resource, Method.PATCH, resource)
    return inner(f) if f else inner


def delete(f=None, resource=None):
    """
    Decorator to indicate a deletion endpoint.

    :param f: Function we are routing
    :param resource: Specify the resource that this function
        encodes/decodes, default is the one specified on the ResourceAPI
        instance.

    """
    def inner(func):
        OperationDoc.bind(func).add_response(HTTPStatus.NO_CONTENT, "Resource has been deleted.")
        return route(func, PathType.Resource, Method.DELETE, resource)
    return inner(f) if f else inner
