"""
Decorators
~~~~~~~~~~

A collection of decorators for identifying the various types of route.

"""
from __future__ import absolute_import

from collections import defaultdict
from typing import Callable, Union, Tuple, Type, Dict, Any, Optional, Generator, List

from odin import Resource
from odin.exceptions import CodecDecodeError
from odin.utils import force_tuple, lazy_property, getmeta

from . import doc
from .constants import *
from .data_structures import NoPath, UrlPath, HttpResponse
from .exceptions import HttpError
from .resources import Listing
from .utils import to_bool, dict_filter

__all__ = (
    'Operation',
    # Basic routes
    'collection', 'collection_action',  # 'resource_route', 'resource_action',
    # Shortcuts
    'listing', 'create', 'detail', 'update', 'patch', 'delete', 'action',  #'detail_action',
)

# Type definitions
Tags = Union[str, Tuple[str]]
HttpRequest = Any
PreDispatch = Callable[[HttpRequest, Dict[str, Any]], HttpResponse]
PostDispatch = Callable[[HttpRequest, HttpResponse], HttpResponse]


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

    def __new__(cls, func=None, *args, **kwargs):
        def inner(callback):
            instance = super(Operation, cls).__new__(cls)
            instance.__init__(callback, *args, **kwargs)
            return instance
        return inner(func) if func else inner

    def __init__(self, callback, url_path=NoPath, methods=Method.GET, resource=None, tags=None, summary=None):
        # type: (Callable, UrlPath, Union(Method, Tuple[Method]), Type[Resource], Tags, Optional(str)) -> None
        """
        :param callback: Function we are routing
        :param url_path: A sub path that can be used as a action.
        :param methods: HTTP method(s) this function responses to.
        :param resource: Specify the resource that this function encodes/decodes,
            default is the one specified on the ResourceAPI instance.
        :param tags: Tags to be applied to operation
        """
        self.base_callback = self.callback = callback
        self.url_path = UrlPath.from_object(url_path)
        self.methods = force_tuple(methods)
        self._resource = resource

        # Sorting/hashing
        self.sort_key = Operation._operation_count
        Operation._operation_count += 1

        # If this operation is bound to a ResourceAPI
        self.binding = None

        # Dispatch hooks
        self._pre_dispatch = getattr(self, 'pre_dispatch', None)  # type: PreDispatch
        self._post_dispatch = getattr(self, 'post_dispatch', None)  # type: PostDispatch

        # Documentation
        self.deprecated = False
        self.summary = summary
        self.consumes = set()
        self.produces = set()
        self.responses = {}
        self._parameters = defaultdict(lambda: defaultdict(dict))
        self._tags = set(force_tuple(tags))

        # Copy values from callback (if defined)
        for attr in ('deprecated', 'consumes', 'produces', 'responses', '_parameters'):
            value = getattr(callback, attr, None)
            if value is not None:
                setattr(self, attr, value)

        # Add a default response
        self.responses.setdefault('default', {
            'description': 'Error',
            'schema': {'$ref': '#/definitions/Error'}
        })

    def __call__(self, request, path_args):
        # type: (HttpRequest, Dict[Any]) -> Any
        """
        Main wrapper around the operation callback function.
        """
        # Allow for a pre_dispatch hook, path_args is passed by ref so changes can be made.
        if self._pre_dispatch:
            self._pre_dispatch(request, path_args)

        response = self.execute(request, **path_args)

        # Allow for a post_dispatch hook, the response of which is returned
        if self._post_dispatch:
            return self._post_dispatch(request, response)
        else:
            return response

    def execute(self, request, *args, **path_args):
        # type: (HttpRequest, tuple, Dict[Any]) -> Any
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

        # Configure hooks
        if self._pre_dispatch is None:
            self._pre_dispatch = getattr(instance, 'pre_dispatch', None)
        if self._post_dispatch is None:
            self._post_dispatch = getattr(instance, 'pos_dispatch', None)

    def op_paths(self, path_prefix=None):
        # type: (Optional[Union[str, UrlPath]]) -> Generator[Tuple[UrlPath, Operation]]
        """
        Yield operations paths stored in containers.
        """
        url_path = self.url_path
        if path_prefix:
            url_path = path_prefix + url_path

        yield url_path, self

    def decode_body(self, request):
        """
        Helper method that ensures that decodes any body content into a string object
        (this is needed by the json module for example).
        """
        body = request.body
        if isinstance(body, bytes):
            return body.decode('UTF8')
        return body

    def get_resource(self, request, allow_multiple=False):
        """
        Get a resource instance from ``request.body``.
        """
        try:
            body = self.decode_body(request)
        except UnicodeDecodeError as ude:
            raise HttpError(HTTPStatus.BAD_REQUEST, 40099, "Unable to decode request body.", str(ude))

        try:
            resource = request.request_codec.loads(body, resource=self.resource, full_clean=False)

        except ValueError as ve:
            raise HttpError(HTTPStatus.BAD_REQUEST, 40098, "Unable to load resource.", str(ve))

        except CodecDecodeError as cde:
            raise HttpError(HTTPStatus.BAD_REQUEST, 40096, "Unable to decode body.", str(cde))

        # Check an array of data hasn't been supplied
        if not allow_multiple and isinstance(resource, list):
            raise HttpError(HTTPStatus.BAD_REQUEST, 40097, "Expected a single resource not a list.")

        return resource

    @lazy_property
    def resource(self):
        """
        Resource associated with operation.
        """
        if self._resource:
            return self._resource
        elif self.binding:
            return self.binding.resource

    @property
    def is_bound(self):
        # type: () -> bool
        """
        Operation is bound to a resource api
        """
        return bool(self.binding)

    # Docs ####################################################################

    def to_doc(self):
        """
        Generate a dictionary for documentation generation.
        """
        return dict_filter(
            operationId=self.operation_id,
            description=(self.callback.__doc__ or '').strip(),
            summary=self.summary,
            tags=self.tags if self.tags else None,
            deprecated=True if self.deprecated else None,
            consumes=self.consumes if self.consumes else None,
            parameters=self.parameters,
            produces=list(self.produces) if self.produces else None,
            responses=self.responses if self.responses else None,
        )

    @lazy_property
    def operation_id(self):
        return self.base_callback.__name__

    @property
    def tags(self):
        # type: () -> List[str]
        """
        Tags applied to operation.
        """
        tags = []
        if self._tags:
            tags.extend(self._tags)
        if self.binding:
            binding_tags = getattr(self.binding, 'tags', None)
            if binding_tags:
                tags.extend(binding_tags)
        return tags

    @property
    def parameters(self):
        """
        Build parameter definition
        """
        results = []

        for param_type in (In.Path, In.Header, In.Query, In.Form):
            results.extend(self._parameters[param_type].values())

        if In.Body in self._parameters:
            body_param = self._parameters[In.Body]
            if self.resource:
                body_param['schema'] = {
                    '$ref': '#/definitions/{}'.format(getmeta(self.resource).resource_name)
                }
            results.append(body_param)

        return results or None

collection = collection_action = action = Operation


class ListOperation(Operation):
    """
    Decorator to indicate a listing endpoint.

    Usage::

        class ItemApi(ResourceApi):
            resource = Item

            @listing(path=PathType.Collection, methods=Method.Get)
            def list_items(self, request, offset, limit):
                ...
                return items

    """
    listing_resource = Listing
    default_offset = 0
    default_limit = 50
    max_offset = None
    max_limit = None

    def __init__(self, callback, url_path=NoPath, methods=Method.GET, resource=None, tags=None,
                 listing_resource=None, default_offset=None, default_limit=None, max_offset=None, max_limit=None):
        super(ListOperation, self).__init__(callback, url_path, methods, resource, tags)
        if listing_resource:
            self.listing_resource = listing_resource
        if default_offset is not None:
            self.default_offset = default_offset
        if default_limit is not None:
            self.default_limit = default_limit
        if max_offset is not None:
            self.max_offset = max_offset
        if max_limit is not None:
            self.max_limit = max_limit

        # Apply documentation
        doc.query_param('offset', Type.Integer, obj=self, description="Offset to start listing from.",
                        default=self.default_offset, maximum=self.max_offset)

    def execute(self, request, *args, **path_args):
        # Get paging args from query string
        max_offset = self.max_offset
        offset = int(request.GET.get('offset', self.default_offset))
        if offset < 0:
            offset = 0
        elif max_offset and offset > max_offset:
            offset = max_offset
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
        result = super(ListOperation, self).execute(request, *args, **path_args)
        if result is not None:
            if isinstance(result, tuple) and len(result) == 2:
                result, total_count = result
            else:
                total_count = None

            return result if bare else Listing(result, limit, offset, total_count)


listing = ListOperation


class ResourceOperation(Operation):
    """
    Handle processing a request with a resource body.

    It is assumed decorator will operate on a class method.
    """
    def __init__(self, *args, **kwargs):
        super(ResourceOperation, self).__init__(*args, **kwargs)

        # Apply documentation
        doc.body(obj=self)

    def execute(self, request, *args, **path_args):
        item = self.get_resource(request) if self.resource else None
        return super(ResourceOperation, self).execute(request, item, *args, **path_args)


resource_request = ResourceOperation


# Shortcut methods


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
