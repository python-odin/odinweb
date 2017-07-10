"""
Decorators
~~~~~~~~~~

A collection of decorators for identifying the various types of route.

"""
from __future__ import absolute_import

from collections import namedtuple
from functools import wraps

from . import _compat
from . import constants
from .resources import Listing

__all__ = (
    # Basic routes
    'route', 'collection', 'collection_action', 'resource_route', 'resource_action',
    # Handlers
    'list_response',
    # Shortcuts
    'listing', 'create', 'detail', 'update', 'patch', 'delete', 'action', 'detail_action',
    # Docs
    'operation_doc', 'parameter_doc', 'response_doc', 'get_docs'
)

# Counter used to order routes
_route_count = 0

# Definition of a route bound to a class method
RouteDefinition = namedtuple("RouteDefinition", ('route_number', 'path_type', 'methods', 'sub_path', 'callback'))


def route(func=None, path_type=constants.PATH_TYPE_COLLECTION, methods=constants.GET, resource=None, sub_path=None):
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


def resource_route(func=None, method=constants.GET, resource=None, sub_path=None):
    return route(func, constants.PATH_TYPE_RESOURCE, method, resource, sub_path)

resource_action = detail_action = resource_route


# Handlers

def list_response(func=None, default_offset=0, default_limit=50):
    """
    Handle processing a list. It is assumed decorator will operate on a class.

    This decorator extracts offer/limit values from the query string and returns
    a Listing response and applies total counts.

    """
    def inner(f):
        _apply_docs(f, parameters=[
            {'name': 'offset',
             'in': constants.IN_QUERY,
             'type': constants.TYPE_INTEGER,
             'default': default_offset},
            {'name': 'limit',
             'in': constants.IN_QUERY,
             'type': constants.TYPE_INTEGER,
             'default': default_limit},
        ])

        @wraps(f)
        def wrapper(self, request, *args, **kwargs):
            # Get paging args from query string
            offset = kwargs['offset'] = int(request.GET.get('offset', default_offset))
            limit = kwargs['limit'] = int(request.GET.get('limit', default_limit))
            result = f(self, request, *args, **kwargs)
            if result is not None:
                if isinstance(result, tuple) and len(result) == 2:
                    result, total_count = result
                else:
                    total_count = None
                return Listing(list(result), limit, offset, total_count)
        return wrapper

    return inner(func) if func else inner


# Shortcut methods

def listing(func=None, resource=None, default_offset=0, default_limit=50):
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
        list_response(func, default_offset, default_limit),
        constants.PATH_TYPE_COLLECTION, constants.GET, resource
    )


def create(func=None, resource=None):
    """
    Decorator to indicate a creation endpoint.

    :param func: Function we are routing
    :param resource: Specify the resource that this function
        encodes/decodes, default is the one specified on the ResourceAPI
        instance.

    """
    return route(func, constants.PATH_TYPE_COLLECTION, constants.POST, resource)


def detail(func=None, resource=None):
    """
    Decorator to indicate a detail endpoint.

    :param func: Function we are routing
    :param resource: Specify the resource that this function
        encodes/decodes, default is the one specified on the ResourceAPI
        instance.

    """
    return route(func, constants.PATH_TYPE_RESOURCE, constants.GET, resource)


def update(func=None, resource=None):
    """
    Decorator to indicate an update endpoint.

    :param func: Function we are routing
    :param resource: Specify the resource that this function
        encodes/decodes, default is the one specified on the ResourceAPI
        instance.

    """
    return route(func, constants.PATH_TYPE_RESOURCE, constants.PUT, resource)


def patch(func=None, resource=None):
    """
    Decorator to indicate a patch endpoint.

    :param func: Function we are routing
    :param resource: Specify the resource that this function
        encodes/decodes, default is the one specified on the ResourceAPI
        instance.

    """
    return route(func, constants.PATH_TYPE_RESOURCE, constants.PATCH, resource)


def delete(func=None, resource=None):
    """
    Decorator to indicate a deletion endpoint.

    :param func: Function we are routing
    :param resource: Specify the resource that this function
        encodes/decodes, default is the one specified on the ResourceAPI
        instance.

    """
    return route(func, constants.PATH_TYPE_RESOURCE, constants.DELETE, resource)


# Documentation methods

def _apply_docs(c, **fields):
    """
    Apply documentation to a callback.
    """
    parameters = fields.pop('parameters', None)
    responses = fields.pop('responses', None)

    def inner(callback):
        docs = getattr(callback, '_OdinWeb_docs', {})

        if fields:
            docs.update({k: v for k, v in fields.items() if v is not None})

        if parameters:
            # Ensure there are no duplicates
            param_map = {}
            for param in docs.get('parameters', []):
                param_map[param['name'] + param['in']] = param

            for param in parameters:
                param_map[param['name'] + param['in']] = param

            docs['parameters'] = param_map.values()

        if responses:
            docs.setdefault('responses', {}).update(responses)

        setattr(callback, '_OdinWeb_docs', docs)
        return callback

    return inner(c) if c else inner


def get_docs(callback):
    # type (func) -> dict
    """
    Get any docs defined by documentation decorators
    """
    docs = getattr(callback, '_OdinWeb_docs', None) or {}
    if callback.__doc__:
        docs.setdefault('description', callback.__doc__.strip())
    return docs


def operation_doc(summary=None, tags=None, deprecated=None):
    """
    Decorator for applying operation documentation to a callback.

    The values are based off `Swagger <https://swagger.io/specification>`_.

    """
    return _apply_docs(None, summary=summary, tags=tags, deprecated=deprecated)


def parameter_doc(name, in_, description=None, required=None, type_=None, default=None):
    """
    Decorator for applying parameter documentation to a callback.

    The values are based off `Swagger <https://swagger.io/specification>`_.

    """
    in_ = in_.title()

    # Include all values that are defined.
    parameter = {k: v for k, v in {
        'name': name,
        'in': in_,
        'description': description,
        'required': required or in_ == constants.IN_PATH,
        'type': type_,
        'default': default,
    }.items() if v is not None}

    return _apply_docs(None, parameters=[parameter])


def response_doc(status, description, resource=None):
    """
    Define an expected responses.

    The values are based off `Swagger <https://swagger.io/specification>`_.

    """
    return _apply_docs(None, responses={
        status: {
            'description': description,
        }
    })
