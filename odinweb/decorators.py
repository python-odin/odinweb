"""
Decorators
~~~~~~~~~~

A collection of decorators for identifying the various types of route.

"""
from __future__ import absolute_import

# Imports for typing support
from typing import Callable, Union, Tuple, Dict, Any, Generator, List, Set, Iterable  # noqa
from odin import Resource  # noqa

from odin.utils import force_tuple, lazy_property, getmeta

from .constants import HTTPStatus, Method, Type
from .data_structures import NoPath, UrlPath, PathParam, Param, Response, DefaultResponse, MiddlewareList
from .helpers import get_resource, create_response
from .resources import Listing, Error
from .utils import to_bool, dict_filter

__all__ = (
    'Operation', 'ListOperation', 'ResourceOperation', 'security',
    # Basic routes
    'collection', 'collection_action', 'action', 'operation',
    # Shortcuts
    'listing', 'create', 'detail', 'update', 'patch', 'delete',
)

# Type definitions
Tags = Union[str, Iterable[str]]
Methods = Union[Method, Iterable[Method]]
Path = Union[UrlPath, str, PathParam]


class Security(object):
    """
    Security definition of an object.
    """
    def __init__(self, name, *permissions):
        # type: (str, str) -> None
        self.name = name
        self.permissions = set(permissions)

    def to_swagger(self):
        """
        Return swagger definition of this object.
        """
        return {self.name: list(self.permissions)}


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
    priority = 100  # Set limit high as this should be the last item

    def __new__(cls, func=None, *args, **kwargs):
        def inner(callback):
            instance = super(Operation, cls).__new__(cls)
            instance.__init__(callback, *args, **kwargs)
            return instance
        return inner(func) if func else inner

    def __init__(self, callback, path=NoPath, methods=Method.GET, resource=None, tags=None, summary=None,
                 middleware=None):
        # type: (Callable, Path, Methods, Resource, Tags, str, List[Any]) -> None
        """
        :param callback: Function we are routing
        :param path: A sub path that can be used as a action.
        :param methods: HTTP method(s) this function responses to.
        :param resource: Specify the resource that this function encodes/decodes,
            default is the one specified on the ResourceAPI instance.
        :param tags: Tags to be applied to operation
        """
        self.base_callback = self.callback = callback
        self.url_path = UrlPath.from_object(path)
        self.methods = force_tuple(methods)
        self._resource = resource

        # Sorting/hashing
        self.sort_key = Operation._operation_count
        Operation._operation_count += 1

        # If this operation is bound to a ResourceAPI
        self.binding = None

        self.middleware = MiddlewareList(middleware or [])
        self.middleware.append(self)  # Add self as middleware to obtain pre-dispatch support

        # Security object
        self.security = None

        # Documentation
        self.deprecated = False
        self.summary = summary
        self.consumes = set()
        self.produces = set()
        self.responses = set()
        self.parameters = set()
        self._tags = set(force_tuple(tags))

        # Copy values from callback (if defined)
        for attr in ('deprecated', 'consumes', 'produces', 'responses', 'parameters', 'security'):
            value = getattr(callback, attr, None)
            if value is not None:
                setattr(self, attr, value)

        # Add a default response
        self.responses.add(DefaultResponse('Unhandled error', Error))

    def __call__(self, request, path_args):
        # type: (Any, Dict[Any]) -> Any
        """
        Main wrapper around the operation callback function.
        """
        # path_args is passed by ref so changes can be made.
        for middleware in self.middleware.pre_dispatch:
            middleware(request, path_args)

        response = self.execute(request, **path_args)

        for middleware in self.middleware.post_dispatch:
            response = middleware(request, response)

        return response

    def __eq__(self, other):
        """
        Compare to Operations to identify if they refer to the same endpoint.

        Basically this means does the URL path and methods match?
        """
        if isinstance(other, Operation):
            return all(
                getattr(self, a) == getattr(other, a)
                for a in ('path', 'methods')
            )
        return NotImplemented

    def __str__(self):
        return "{} - {} {}".format(self.operation_id, '|'.join(m.value for m in self.methods), self.path)

    def __repr__(self):
        return "Operation({!r}, {!r}, {})".format(self.operation_id, self.path, self.methods)

    def execute(self, request, *args, **path_args):
        # type: (Any, tuple, Dict[Any]) -> Any
        """
        Execute the callback (binding callback if required)
        """
        binding = self.binding
        if binding:
            # Provide binding as decorators are executed prior to binding
            return self.callback(binding, request, *args, **path_args)
        else:
            return self.callback(request, *args, **path_args)

    def bind_to_instance(self, instance):
        """
        Bind a ResourceApi instance to an operation.
        """
        self.binding = instance
        self.middleware.append(instance)

    def op_paths(self, path_prefix=None):
        # type: (Path) -> Generator[Tuple[UrlPath, Operation]]
        """
        Yield operations paths stored in containers.
        """
        url_path = self.path
        if path_prefix:
            url_path = path_prefix + url_path

        yield url_path, self

    @lazy_property
    def path(self):
        """
        Prepared and setup URL Path.
        """
        return self.url_path.apply_args(key_field=self.key_field_name)

    @property
    def resource(self):
        """
        Resource associated with operation.
        """
        if self._resource:
            return self._resource
        elif self.binding:
            return self.binding.resource

    @lazy_property
    def key_field_name(self):
        """
        Field identified as the key.
        """
        name = 'resource_id'
        if self.resource:
            key_field = getmeta(self.resource).key_field
            if key_field:
                name = key_field.attname
        return name

    @property
    def is_bound(self):
        # type: () -> bool
        """
        Operation is bound to a resource api
        """
        return bool(self.binding)

    # Docs ####################################################################

    def to_swagger(self):
        """
        Generate a dictionary for documentation generation.
        """
        return dict_filter(
            operationId=self.operation_id,
            description=(self.callback.__doc__ or '').strip() or None,
            summary=self.summary or None,
            tags=list(self.tags) or None,
            deprecated=self.deprecated or None,
            consumes=list(self.consumes) or None,
            parameters=[param.to_swagger(self.resource) for param in self.parameters] or None,
            produces=list(self.produces) or None,
            responses=dict(resp.to_swagger(self.resource) for resp in self.responses) or None,
            security=self.security.to_swagger() if self.security else None,
        )

    @lazy_property
    def operation_id(self):
        return "{}.{}".format(self.base_callback.__module__, self.base_callback.__name__)

    @property
    def tags(self):
        # type: () -> Set[str]
        """
        Tags applied to operation.
        """
        tags = set()
        if self._tags:
            tags.update(self._tags)
        if self.binding:
            binding_tags = getattr(self.binding, 'tags', None)
            if binding_tags:
                tags.update(binding_tags)
        return tags


collection = collection_action = operation = Operation


def security(name, permissions):
    """
    Decorator to add security definition.
    """
    def inner(c):
        c.security = Security(name, permissions)
        return c
    return inner


def action(callback=None, name=None, path=None, methods=Method.GET, resource=None, tags=None,
           summary=None, middleware=None):
    # type: (Callable, Path, Path, Methods, Resource, Tags, str, List[Any]) -> Operation
    """
    Decorator to apply an action to a resource. An action is applied to a `detail` operation.
    """
    # Generate action path
    path = path or '{key_field}'
    if name:
        path += name

    def inner(c):
        return Operation(c, path, methods, resource, tags, summary, middleware)
    return inner(callback) if callback else inner


class WrappedListOperation(Operation):
    """
    Decorator to indicate a listing endpoint that uses a listing wrapper.

    Usage::

        class ItemApi(ResourceApi):
            resource = Item

            @listing(path=PathType.Collection, methods=Method.Get)
            def list_items(self, request, offset, limit):
                ...
                return items

    """
    listing_resource = Listing
    """
    Resource used to wrap listings.
    """

    default_offset = 0
    """
    Default offset if not specified.
    """

    default_limit = 50
    """
    Default limit of not specified.
    """

    max_limit = None
    """
    Maximum limit.
    """

    def __init__(self, *args, **kwargs):
        self.listing_resource = kwargs.pop('listing_resource', self.listing_resource)
        self.default_offset = kwargs.pop('default_offset', self.default_offset)
        self.default_limit = kwargs.pop('default_limit', self.default_limit)
        self.max_limit = kwargs.pop('max_limit', self.max_limit)

        super(WrappedListOperation, self).__init__(*args, **kwargs)

        # Apply documentation
        self.parameters.add(Param.query('offset', Type.Integer, "Offset to start listing from.",
                                        default=self.default_offset))
        self.parameters.add(Param.query('limit', Type.Integer, "Limit on the number of listings returned.",
                                        default=self.default_limit, maximum=self.max_limit))
        self.parameters.add(Param.query('bare', Type.Boolean, "Return a plain list of objects."))

    def execute(self, request, *args, **path_args):
        # Get paging args from query string
        offset = int(request.GET.get('offset', self.default_offset))
        if offset < 0:
            offset = 0
        path_args['offset'] = offset

        max_limit = self.max_limit
        limit = int(request.GET.get('limit', self.default_limit))
        if limit < 1:
            limit = 1
        elif max_limit and limit > max_limit:
            limit = max_limit
        path_args['limit'] = limit

        bare = to_bool(request.GET.get('bare', False))

        # Run base execute
        result = super(WrappedListOperation, self).execute(request, *args, **path_args)
        if result is not None:
            if isinstance(result, tuple) and len(result) == 2:
                result, total_count = result
            else:
                total_count = None

            return result if bare else Listing(result, limit, offset, total_count)


class ListOperation(Operation):
    """
    Decorator to indicate a listing endpoint that does not use a container.

    Usage::

        class ItemApi(ResourceApi):
            resource = Item

            @listing(path=PathType.Collection, methods=Method.Get)
            def list_items(self, request, offset, limit):
                ...
                return items

    """
    default_offset = 0
    """
    Default offset if not specified.
    """

    default_limit = 50
    """
    Default limit of not specified.
    """

    max_limit = None
    """
    Maximum limit.
    """

    def __init__(self, *args, **kwargs):
        self.default_offset = kwargs.pop('default_offset', self.default_offset)
        self.default_limit = kwargs.pop('default_limit', self.default_limit)
        self.max_limit = kwargs.pop('max_limit', self.max_limit)

        super(ListOperation, self).__init__(*args, **kwargs)

        # Apply documentation
        self.parameters.add(Param.query('offset', Type.Integer, "Offset to start listing from.",
                                        default=self.default_offset))
        self.parameters.add(Param.query('limit', Type.Integer, "Limit on the number of listings returned.",
                                        default=self.default_limit, maximum=self.max_limit))

    def execute(self, request, *args, **path_args):
        # Get paging args from query string
        offset = int(request.GET.get('offset', self.default_offset))
        if offset < 0:
            offset = 0
        path_args['offset'] = offset

        max_limit = self.max_limit
        limit = int(request.GET.get('limit', self.default_limit))
        if limit < 1:
            limit = 1
        elif max_limit and limit > max_limit:
            limit = max_limit
        path_args['limit'] = limit

        # Run base execute
        result = super(ListOperation, self).execute(request, *args, **path_args)
        if result is not None:
            headers = {
                'X-Page-Limit': str(limit),
                'X-Page-Offset': str(offset),
            }
            if isinstance(result, tuple) and len(result) == 2:
                result, total_count = result
                if total_count is not None:
                    headers['X-Total-Count'] = str(total_count)

            return create_response(request, result, headers=headers)


class ResourceOperation(Operation):
    """
    Handle processing a request with a resource body.

    It is assumed decorator will operate on a class method.
    """
    def __init__(self, *args, **kwargs):
        self.full_clean = kwargs.pop('full_clean', True)
        self.default_to_not_supplied = kwargs.pop('default_to_not_supplied', False)

        super(ResourceOperation, self).__init__(*args, **kwargs)

        # Apply documentation
        self.parameters.add(Param.body('Expected resource supplied with request.'))

    def execute(self, request, *args, **path_args):
        item = None
        if self.resource:
            item = get_resource(request, self.resource, full_clean=self.full_clean,
                                default_to_not_supplied=self.default_to_not_supplied)
            # Don't allow key_field to be edited
            if hasattr(item, self.key_field_name):
                setattr(item, self.key_field_name, None)
        return super(ResourceOperation, self).execute(request, item, *args, **path_args)


# Shortcut methods

def listing(callback=None, path=None, method=Method.GET, resource=None, tags=None, summary="List resources",
            middleware=None, default_limit=50, max_limit=None, use_wrapper=True):
    # type: (Callable, Path, Methods, Resource, Tags, str, List[Any], int, int) -> Operation
    """
    Decorator to configure an operation that returns a list of resources.
    """
    op_type = WrappedListOperation if use_wrapper else ListOperation

    def inner(c):
        op = op_type(c, path or NoPath, method, resource, tags, summary, middleware,
                     default_limit=default_limit, max_limit=max_limit)
        op.responses.add(Response(HTTPStatus.OK, "Listing of resources", Listing))
        return op
    return inner(callback) if callback else inner


def create(callback=None, path=None, method=Method.POST, resource=None, tags=None, summary="Create a new resource",
           middleware=None):
    # type: (Callable, Path, Methods, Resource, Tags, str, List[Any]) -> Operation
    """
    Decorator to configure an operation that creates a resource.
    """
    def inner(c):
        op = ResourceOperation(c, path or NoPath, method, resource, tags, summary, middleware)
        op.responses.add(Response(HTTPStatus.CREATED, "{name} has been created"))
        op.responses.add(Response(HTTPStatus.BAD_REQUEST, "Validation failed.", Error))
        return op
    return inner(callback) if callback else inner


def detail(callback=None, path=None, method=Method.GET, resource=None, tags=None, summary="Get specified resource.",
           middleware=None):
    # type: (Callable, Path, Methods, Resource, Tags, str, List[Any]) -> Operation
    """
    Decorator to configure an operation that fetches a resource.
    """
    def inner(c):
        op = Operation(c, path or PathParam('{key_field}'), method, resource, tags, summary, middleware)
        op.responses.add(Response(HTTPStatus.OK, "Get a {name}"))
        op.responses.add(Response(HTTPStatus.NOT_FOUND, "Not found", Error))
        return op
    return inner(callback) if callback else inner


def update(callback=None, path=None, method=Method.PUT, resource=None, tags=None, summary="Update specified resource.",
           middleware=None):
    # type: (Callable, Path, Methods, Resource, Tags, str, List[Any]) -> Operation
    """
    Decorator to configure an operation that updates a resource.
    """
    def inner(c):
        op = ResourceOperation(c, path or PathParam('{key_field}'), method, resource, tags, summary, middleware)
        op.responses.add(Response(HTTPStatus.NO_CONTENT, "{name} has been updated."))
        op.responses.add(Response(HTTPStatus.BAD_REQUEST, "Validation failed.", Error))
        op.responses.add(Response(HTTPStatus.NOT_FOUND, "Not found", Error))
        return op
    return inner(callback) if callback else inner


def patch(callback=None, path=None, method=Method.PATCH, resource=None, tags=None, summary="Patch specified resource.",
          middleware=None):
    # type: (Callable, Path, Methods, Resource, Tags, str, List[Any]) -> Operation
    """
    Decorator to configure an operation that patches a resource.
    """
    def inner(c):
        op = ResourceOperation(c, path or PathParam('{key_field}'), method, resource, tags, summary, middleware,
                               full_clean=False, default_to_not_supplied=True)
        op.responses.add(Response(HTTPStatus.OK, "{name} has been patched."))
        op.responses.add(Response(HTTPStatus.BAD_REQUEST, "Validation failed.", Error))
        op.responses.add(Response(HTTPStatus.NOT_FOUND, "Not found", Error))
        return op
    return inner(callback) if callback else inner


def delete(callback=None, path=None, method=Method.DELETE, tags=None, summary="Delete specified resource.",
           middleware=None):
    # type: (Callable, Path, Methods, Tags, str, List[Any]) -> Operation
    """
    Decorator to configure an operation that deletes resource.
    """
    def inner(c):
        op = Operation(c, path or PathParam('{key_field}'), method, None, tags, summary, middleware)
        op.responses.add(Response(HTTPStatus.NO_CONTENT, "{name} has been deleted.", None))
        op.responses.add(Response(HTTPStatus.NOT_FOUND, "Not found", Error))
        return op
    return inner(callback) if callback else inner
