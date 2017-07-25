"""
API
~~~

"""
from __future__ import absolute_import, unicode_literals

import logging

from typing import Callable, Union, Tuple, List, Any, Optional, AnyStr, Dict

from odin import Resource
from odin.codecs import json_codec
from odin.exceptions import ValidationError, CodecDecodeError
from odin.utils import getmeta, lazy_property, force_tuple

from . import _compat
from . import content_type_resolvers
from .data_structures import UrlPath, HttpResponse
from .exceptions import ImmediateHttpResponse, HttpError
from .resources import Error
from .utils import parse_content_type

# Import all to simplify end user API.
from .constants import *  # noqa
# from .decorators import *  # noqa

logger = logging.getLogger(__name__)


CODECS = {json_codec.CONTENT_TYPE: json_codec}

# Attempt to load other codecs that have dependencies
try:
    from odin.codecs import msgpack_codec
    CODECS[msgpack_codec.CONTENT_TYPE] = msgpack_codec
except ImportError:
    pass

try:
    from odin.codecs import yaml_codec
    CODECS[yaml_codec.CONTENT_TYPE] = yaml_codec
except ImportError:
    pass


def resolve_content_type(type_resolvers, request):
    """
    Resolve content types from a request.
    """
    for resolver in type_resolvers:
        content_type = parse_content_type(resolver(request))
        if content_type:
            return content_type


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

    @classmethod
    def decorate(cls, func=None, url_path=None, methods=Method.GET, resource=None, tags=None):
        # type: (Callable, UrlPath, Union(Method, Tuple[Method]), Type[Resource], Tags) -> Operation
        """
        :param func: Function we are routing
        :param url_path: A sub path that can be used as a action.
        :param methods: HTTP method(s) this function responses to.
        :param resource: Specify the resource that this function encodes/decodes,
            default is the one specified on the ResourceAPI instance.
        :param tags: Tags to be applied to operation
        """
        def inner(f):
            return cls(f, url_path, methods, resource, tags)
        return inner(func) if func else inner

    def __init__(self, callback, url_path, methods, resource, tags):
        # type: (Callable, UrlPath, Union(Method, Tuple[Method]), Type[Resource], Tags) -> None
        self.base_callback = self.callback = callback
        self.url_path = url_path
        self.methods = force_tuple(methods)
        self._resource = resource
        self._tags = tags

        self._hash_id = Operation._operation_count
        Operation._operation_count += 1

        # If this operation is bound to a ResourceAPI
        self.binding = None

        # Dispatch hooks
        self._pre_dispatch = getattr(self, 'pre_dispatch', None)  # type: PreDispatch
        self._post_dispatch = getattr(self, 'post_dispatch', None)  # type: PostDispatch

    def __hash__(self):
        return self._hash_id

    def __call__(self, request, path_args):
        # type: (HttpRequest, Dict[Any]) -> Any

        # Allow for a pre_dispatch hook, path_args is passed by ref so changes can be made.
        if self._pre_dispatch:
            self._pre_dispatch(request, path_args)

        response = self.callback(request, **path_args)

        # Allow for a post_dispatch hook, the response of which is returned
        if self._post_dispatch:
            return self._post_dispatch(request, response)
        else:
            return response

    def bind_to_instance(self, instance):
        self.binding = instance

        # Configure pre-bindings
        if self._pre_dispatch is None:
            self._pre_dispatch = getattr(instance, 'pre_dispatch', None)
        if self._post_dispatch is None:
            self._post_dispatch = getattr(instance, 'pos_dispatch', None)

    def op_paths(self, path_prefix=None):
        # type: (Optional[Union[str, UrlPath]]) -> Tuple[Tuple[UrlPath, Operation]]
        """
        Yield operations paths stored in containers.
        """
        url_path = self.url_path
        if path_prefix:
            url_path = path_prefix + url_path

        yield url_path, self

    @property
    def is_bound(self):
        # type: () -> bool
        """
        Operation is bound to a resource api
        """
        return bool(self.binding)

    @lazy_property
    def operation_id(self):
        return self.base_callback.__name__

    @lazy_property
    def resource(self):
        """
        Resource associated with operation.
        """
        if self.resource:
            return self.resource
        elif self.binding:
            return self.binding.resource

    @lazy_property
    def tags(self):
        # type: () -> List[AnyStr]
        """
        Tags applied to operation.
        """
        tags = []
        if self._tags:
            tags.extend(self._tags)
        if self.binding and self.binding.tags:
            tags.extend(self.binding.tags)
        return tags


class ResourceApiMeta(type):
    """
    Meta class that resolves endpoints to routes.
    """
    def __new__(mcs, name, bases, attrs):
        super_new = super(ResourceApiMeta, mcs).__new__

        # attrs will never be empty for classes declared in the standard way
        # (ie. with the `class` keyword). This is quite robust.
        if name == 'NewBase' and attrs == {}:
            return super_new(mcs, name, bases, attrs)

        parents = [
            b for b in bases
            if isinstance(b, ResourceApiMeta) and not (b.__name__ == 'NewBase' and b.__mro__ == (b, object))
        ]
        if not parents:
            # If this isn't a subclass of don't do anything special.
            return super_new(mcs, name, bases, attrs)

        # Determine the resource used by this API (handle inherited resources)
        api_resource = attrs.get('resource')
        if api_resource is None:
            for base in bases:
                api_resource = base.resource
                if api_resource:
                    break

        # Get operations
        operations = []
        for view, obj in attrs.items():
            if isinstance(obj, Operation):
                operations.append(obj)

        # Get routes from parent objects
        for parent in parents:
            if hasattr(parent, '_operations'):
                operations.extend(parent._operations)

        new_class = super_new(mcs, name, bases, attrs)
        new_class._operations = sorted(operations, key=hash)

        return new_class


class ResourceApi(_compat.with_metaclass(ResourceApiMeta)):
    """
    Base framework specific ResourceAPI implementations.
    """
    resource = None
    """
    The resource this API is modelled on.
    """

    resource_id_type = Type.Integer
    """
    Resource ID type.
    """

    resource_id_name = 'resource_id'
    """
    Name of the resource ID field
    """

    path_prefix = []
    """
    Prefix to prepend to any generated path.
    """

    parent = None

    def __init__(self):
        if not hasattr(self, 'api_name'):
            self.api_name = "{}".format(getmeta(self.resource).name.lower())

        self._api_routes = None

        for operation in self._operations:
            operation.bind_to_instance(self)

    @property
    def debug_enabled(self):
        """
        Is debugging enabled?
        """
        if self.parent:
            return self.parent.debug_enabled
        return False

    def dispatch(self, callback, request, **path_args):
        # Authorisation hook
        if hasattr(self, 'handle_authorisation'):
            self.handle_authorisation(request)

        # Allow for a pre_dispatch hook, a response from pre_dispatch would indicate an override of kwargs
        if hasattr(self, 'pre_dispatch'):
            response = self.pre_dispatch(request, **path_args)
            if response is not None:
                path_args = response

        # callbacks are obtained prior to binding hence methods are unbound and self needs to be supplied.
        result = callback(self, request, **path_args)

        # Allow for a post_dispatch hook, the response of which is returned
        if hasattr(self, 'post_dispatch'):
            return self.post_dispatch(request, result)
        else:
            return result

    def decode_body(self, request):
        """
        Helper method that ensures that decodes any body content into a string object
        (this is needed by the json module for example).
        """
        body = request.body
        if isinstance(body, bytes):
            return body.decode('UTF8')
        return body

    def get_resource(self, request, allow_multiple=False, resource=None):
        """
        Get a resource instance from ``request.body``.
        """
        resource = resource or self.resource

        try:
            body = self.decode_body(request)
        except UnicodeDecodeError as ude:
            raise HttpError(HTTPStatus.BAD_REQUEST, 40099, "Unable to decode request body.", str(ude))

        try:
            resource = request.request_codec.loads(body, resource=resource, full_clean=False)

        except ValueError as ve:
            raise HttpError(HTTPStatus.BAD_REQUEST, 40098, "Unable to load resource.", str(ve))

        except CodecDecodeError as cde:
            raise HttpError(HTTPStatus.BAD_REQUEST, 40096, "Unable to decode body.", str(cde))

        # Check an array of data hasn't been supplied
        if not allow_multiple and isinstance(resource, list):
            raise HttpError(HTTPStatus.BAD_REQUEST, 40097, "Expected a single resource not a list.")

        return resource


class ApiContainer(object):
    """
    Container or API endpoints.
    
    This class is intended as a base class for other API classes. Containers
    can also be nested. This is used to support versions etc.
    
    """
    def __init__(self, *containers, **options):
        # type: (*Union[Operation, ApiContainer], **Any) -> None
        self.containers = containers

        # Having options at the end is  work around until support for
        # Python < 3.5 is dropped, at that point keyword only args will
        # be used in place of the options kwargs. eg:
        #   (*containers:Union[Operation, ApiContainer], name:str=None, path_prefix:Union[str, UrlPath]=None) -> None
        self.name = name = options.pop('name', None)
        path_prefix = options.pop('path_prefix', None)
        if path_prefix:
            self.path_prefix = UrlPath.from_object(path_prefix)
        elif name:
            self.path_prefix = UrlPath.parse(name)
        else:
            self.path_prefix = UrlPath()

        if options:
            raise TypeError("Got an unexpected keyword argument(s) {}", options.keys())

    def op_paths(self, path_base=None):
        # type: (Optional[Union[str, UrlPath]]) -> List[Operation]
        """
        Return all operations stored in containers.
        """
        if path_base:
            if self.path_prefix:
                path_base += self.path_prefix
        else:
            path_base = self.path_prefix or UrlPath()

        for container in self.containers:
            container.parent = self
            for op_path in container.op_paths(path_base):
                yield op_path


class ApiCollection(ApiContainer):
    """
    A collection of API endpoints
    """
    parent = None

    @property
    def debug_enabled(self):
        """
        Is debugging enabled?
        """
        if self.parent:
            return self.parent.debug_enabled
        return False


class ApiVersion(ApiCollection):
    """
    Collection that defines a version of an API.
    """
    def __init__(self, *containers, **options):
        # type: (*Union[Operation, ApiContainer], **Any) -> None
        self.version = options.pop('version', 1)
        options.setdefault('name', 'v{}'.format(self.version))
        super(ApiVersion, self).__init__(*containers, **options)


class ApiInterfaceBase(ApiContainer):
    """
    Base class for API interfaces. 
    
    API interfaces are the interfaces between OdinWeb and the web framework 
    being used.
    
    """
    registered_codecs = CODECS
    """
    Codecs that are supported by this API.
    """

    request_type_resolvers = [
        content_type_resolvers.content_type_header(),
        content_type_resolvers.accepts_header(),
        content_type_resolvers.specific_default(json_codec.CONTENT_TYPE),
    ]
    """
    Collection of resolvers used to identify the content type of the request.
    """

    response_type_resolvers = [
        content_type_resolvers.accepts_header(),
        content_type_resolvers.content_type_header(),
        content_type_resolvers.specific_default(json_codec.CONTENT_TYPE),
    ]
    """
    Collection of resolvers used to identify the content type of the response.
    """

    remap_codecs = {
        'text/plain': 'application/json'
    }
    """
    Remap certain codecs commonly mistakenly used.
    """

    def __init__(self, *containers, **options):
        options.setdefault('name', 'api')
        options.setdefault('path_prefix', UrlPath('', options['name']))
        self.debug_enabled = options.pop('debug_enabled', False)
        super(ApiInterfaceBase, self).__init__(*containers, **options)

        if not self.path_prefix.is_absolute:
            raise ValueError("Path prefix must be an absolute path (eg start with a '/')")

    def handle_500(self, request, exception):
        """
        Handle an *un-handled* exception.
        """
        logger.exception('Internal Server Error: %s', exception, extra={
            'status_code': 500,
            'request': request
        })
        return Error.from_status(HTTPStatus.INTERNAL_SERVER_ERROR, 0,
                                 "An unhandled error has been caught.")

    def dispatch(self, operation, request, **path_args):
        """
        Dispatch incoming request to operation.
        """
        # Determine the request and response types. Ensure API supports the requested types
        request_type = resolve_content_type(self.request_type_resolvers, request)
        request_type = self.remap_codecs.get(request_type, request_type)
        try:
            request.request_codec = self.registered_codecs[request_type]
        except KeyError:
            return HttpResponse.from_status(HTTPStatus.UNPROCESSABLE_ENTITY)

        response_type = resolve_content_type(self.response_type_resolvers, request)
        response_type = self.remap_codecs.get(response_type, response_type)
        try:
            request.response_codec = self.registered_codecs[response_type]
        except KeyError:
            return HttpResponse.from_status(HTTPStatus.NOT_ACCEPTABLE)

        # Check if method is in our allowed method list
        if request.method not in operation.methods:
            return HttpResponse.from_status(HTTPStatus.METHOD_NOT_ALLOWED, {'Allow', ','.join(operation.methods)})

        # Response types
        status = headers = None

        try:
            resource = operation(request, **path_args)

        except ImmediateHttpResponse as e:
            # An exception used to return a response immediately, skipping any
            # further processing.
            resource, status, headers = e.resource, e.status, e.headers

        except ValidationError as e:
            # A validation error was raised by a resource.
            if hasattr(e, 'message_dict'):
                resource = Error.from_status(HTTPStatus.BAD_REQUEST, 0, "Failed validation", meta=e.message_dict)
            else:
                resource = Error.from_status(HTTPStatus.BAD_REQUEST, 0, str(e))
            status = resource.status

        except NotImplementedError:
            resource = Error.from_status(HTTPStatus.NOT_IMPLEMENTED, 0, "The method has not been implemented")
            status = resource.status

        except Exception as e:
            if self.debug_enabled:
                # If debug is enabled then fallback to the frameworks default
                # error processing, this often provides convenience features
                # to aid in the debugging process.
                raise
            resource = self.handle_500(request, e)
            status = resource.status

        if isinstance(status, HTTPStatus):
            status = status.value

        # Return a HttpResponse and just send it!
        if isinstance(resource, HttpResponse):
            return resource

        return self.create_response(request, resource, status, headers)

    def create_response(self, request, body=None, status=None, headers=None):
        """
        Generate a HttpResponse.

        :param request: Request object 
        :param body: Body of the response
        :param status: HTTP status code
        :param headers: Any headers.

        """
        if body is None:
            return HttpResponse(None, status or HTTPStatus.NO_CONTENT, headers)

        try:
            body = request.response_codec.dumps(body)
        except Exception as ex:
            if self.debug_enabled:
                # If debug is enabled then fallback to the frameworks default
                # error processing, this often provides convenience features
                # to aid in the debugging process.
                raise
            # Use a high level exception handler as the JSON codec can
            # return a large array of errors.
            self.handle_500(request, ex)
            return HttpResponse("Error encoding response.", HTTPStatus.INTERNAL_SERVER_ERROR)
        else:
            response = HttpResponse(body, status or HTTPStatus.OK, headers)
            response.set_content_type(request.response_codec.CONTENT_TYPE)
            return response
