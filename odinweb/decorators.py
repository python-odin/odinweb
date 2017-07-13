"""
Decorators
~~~~~~~~~~

A collection of decorators for identifying the various types of route.

"""
from __future__ import absolute_import

from collections import namedtuple
from functools import wraps

from odinweb.utils import to_bool
from . import _compat
from .doc import OperationDoc
from .constants import *
from .resources import Listing

__all__ = (
    # Basic routes
    'route', 'collection', 'collection_action', 'resource_route', 'resource_action',
    # Handlers
    'list_response',
    # Shortcuts
    'listing', 'create', 'detail', 'update', 'patch', 'delete', 'action', 'detail_action',
)

# Counter used to order routes
_route_count = 0

# Definition of a route bound to a class method
RouteDefinition = namedtuple("RouteDefinition", 'route_number path_type methods sub_path callback')


def route(func=None, path_type=PathType.Collection, methods=GET, resource=None, sub_path=None):
    """
    Decorator for defining an API route. Usually one of the helpers (listing, detail, update, delete) would be
    used in place of the route decorator.

    Usage::

        class ItemApi(ResourceApi):
            resource = Item

            @route(path=PATH_TYPE_LIST, methods=GET)
            def list_items(self, request):
                ...
                return items

    :param func: Function we are routing
    :param sub_path: A sub path that can be used as a action.
    :param path_type: Type of path, list/detail or custom.
    :param methods: HTTP method(s) this function responses to.
    :type methods: str | tuple(str) | list(str)
    :param resource: Specify the resource that this function encodes/decodes,
        default is the one specified on the ResourceAPI instance.

    """
    if isinstance(methods, _compat.string_types):
        methods = (methods, )

    # Generate a route number
    global _route_count
    route_number = _route_count
    _route_count += 1

    if sub_path:
        # If we have a sub path normalise it into a tuple.
        if isinstance(sub_path, _compat.string_types):
            sub_path = (sub_path,)
        elif not isinstance(sub_path, (list, tuple)):
            sub_path = tuple(sub_path,)

    def inner(f):
        f.route = RouteDefinition(route_number, path_type, methods, sub_path, f)
        f.resource = resource
        return f

    return inner(func) if func else inner

collection = collection_action = action = route


def resource_route(func=None, method=GET, resource=None, sub_path=None):
    return route(func, PathType.Resource, method, resource, sub_path)

resource_action = detail_action = resource_route


# Handlers

def list_response(func=None, max_offset=None, default_offset=0, max_limit=None, default_limit=50):
    """
    Handle processing a list. It is assumed decorator will operate on a class.

    This decorator extracts offer/limit values from the query string and returns
    a Listing response and applies total counts.

    """
    def inner(f):
        docs = OperationDoc.get(f)
        docs.add_parameter('offset', In.Query.value, type=Type.Integer.value,
                           default=default_offset, minimum=0, maximum=max_offset)
        docs.add_parameter('limit', In.Query.value, type=Type.Integer.value,
                           default=default_limit, minimum=1, maximum=max_limit)
        docs.add_parameter('bare', In.Query.value, type=Type.Boolean.value, default=False)
        docs.add_response(200, 'OK', Listing)

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


# Shortcut methods

def listing(func=None, resource=Listing, max_offset=None, default_offset=0, max_limit=None, default_limit=50):
    """
    Decorator to indicate a listing endpoint.

    :param func: Function we are routing
    :param resource: Specify the resource that this function
        encodes/decodes, default is the one specified on the ResourceAPI
        instance.
    :param default_offset: Default value for the offset from the start of listing.
    :param default_limit: Default value for limiting the response size.

    """
    return route(
        list_response(func, max_offset, default_offset, max_limit, default_limit),
        PathType.Collection, GET, resource
    )


def create(func=None, resource=None):
    """
    Decorator to indicate a creation endpoint.

    :param func: Function we are routing
    :param resource: Specify the resource that this function
        encodes/decodes, default is the one specified on the ResourceAPI
        instance.

    """
    return route(func, PathType.Collection, POST, resource)


def detail(func=None, resource=None):
    """
    Decorator to indicate a detail endpoint.

    :param func: Function we are routing
    :param resource: Specify the resource that this function
        encodes/decodes, default is the one specified on the ResourceAPI
        instance.

    """
    return route(func, PathType.Resource, GET, resource)


def update(func=None, resource=None):
    """
    Decorator to indicate an update endpoint.

    :param func: Function we are routing
    :param resource: Specify the resource that this function
        encodes/decodes, default is the one specified on the ResourceAPI
        instance.

    """
    return route(func, PathType.Resource, PUT, resource)


def patch(func=None, resource=None):
    """
    Decorator to indicate a patch endpoint.

    :param func: Function we are routing
    :param resource: Specify the resource that this function
        encodes/decodes, default is the one specified on the ResourceAPI
        instance.

    """
    return route(func, PathType.Resource, PATCH, resource)


def delete(func=None, resource=None):
    """
    Decorator to indicate a deletion endpoint.

    :param func: Function we are routing
    :param resource: Specify the resource that this function
        encodes/decodes, default is the one specified on the ResourceAPI
        instance.

    """
    return route(func, PathType.Resource, DELETE, resource)
