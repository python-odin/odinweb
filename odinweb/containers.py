"""
API Containers
~~~~~~~~~~~~~~

Containers that provide structure to an API.

"""
from __future__ import absolute_import

import logging

# Imports for typing support
from typing import Callable, Union, Tuple, List, Any, Optional, Generator  # noqa
from odin import Resource  # noqa

from odin.codecs import json_codec
from odin.exceptions import ValidationError
from odin.utils import getmeta

from . import _compat
from . import content_type_resolvers
from .constants import Type, Method, HTTPStatus
from .data_structures import UrlPath, NoPath, HttpResponse, MiddlewareList
from .decorators import Operation
from .exceptions import ImmediateHttpResponse
from .helpers import resolve_content_type, create_response
from .resources import Error

__all__ = ('ResourceApi', 'ApiCollection', 'ApiVersion')

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
        for obj in attrs.values():
            if isinstance(obj, Operation):
                operations.append(obj)

        # Get routes from parent objects
        for parent in parents:
            parent_ops = getattr(parent, '_operations', None)
            if parent_ops:
                operations.extend(parent_ops)

        new_class = super_new(mcs, name, bases, attrs)
        setattr(new_class, '_operations', sorted(operations, key=lambda o: o.sort_key))

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

    path_prefix = UrlPath()
    """
    Prefix to prepend to any generated path.
    """

    tags = None
    """
    Resource API tags
    """

    parent = None

    def __init__(self):
        if not hasattr(self, 'api_name'):
            self.api_name = "{}".format(getmeta(self.resource).name.lower())

        # Append APIs name to path prefix
        self.path_prefix += self.api_name

        for operation in self._operations:
            operation.bind_to_instance(self)

    def op_paths(self, path_base):
        # type: (Union[str, UrlPath]) -> Generator[Tuple[UrlPath, Operation]]
        """
        Return all operations stored in containers.
        """
        path_base += self.path_prefix

        for operation in self._operations:
            for op_path in operation.op_paths(path_base):
                yield op_path


class ApiContainer(object):
    """
    Container or API endpoints.
    
    This class is intended as a base class for other API classes. Containers
    can also be nested. This is used to support versions etc.
    
    """
    def __init__(self, *containers, **options):
        # type: (*Union[Operation, ApiContainer, ResourceApi], **Any) -> None
        self.containers = list(containers)

        # Set self as the parent
        for container in self.containers:
            container.parent = self

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
            self.path_prefix = NoPath

        if options:
            raise TypeError("Got an unexpected keyword argument(s) {}", options.keys())

    def operation(self, func=None, url_path=None, methods=Method.GET, resource=None, tags=None):
        # type: (Callable, UrlPath, Union(Method, Tuple[Method]), Type[Resource], Tags) -> Operation
        """
        :param func: Function we are routing
        :param url_path: A sub path that can be used as a action.
        :param methods: HTTP method(s) this function responses to.
        :param resource: Specify the resource that this function encodes/decodes,
            default is the one specified on the ResourceAPI instance.
        :param tags: Tags to be applied to operation

        """
        def inner(callback):
            operation = Operation(callback, url_path, methods, resource, tags)
            self.containers.append(operation)
            return operation

        return inner(func) if func else inner

    def op_paths(self, path_base=None):
        # type: (Optional[Union[str, UrlPath]]) -> List[Tuple[UrlPath, Operation]]
        """
        Return all operations stored in containers.
        """
        if path_base:
            if self.path_prefix:
                path_base += self.path_prefix
        else:
            path_base = self.path_prefix or UrlPath()

        for container in self.containers:
            for op_path in container.op_paths(path_base):
                yield op_path


class ApiCollection(ApiContainer):
    """
    A collection of API endpoints
    """
    parent = None


class ApiVersion(ApiCollection):
    """
    Collection that defines a version of an API.
    """
    def __init__(self, *containers, **options):
        # type: (*Union[Operation, ApiContainer, ResourceApi], **Any) -> None
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
        self.middleware = MiddlewareList(options.pop('middleware', []))
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
            return HttpResponse.from_status(
                HTTPStatus.METHOD_NOT_ALLOWED,
                {'Allow': ','.join(m.value for m in operation.methods)}
            )

        # Response types
        status = headers = None

        try:
            # path_args is passed by ref so changes can be made.
            for middleware in self.middleware.pre_dispatch:
                middleware(request, path_args)

            resource = operation(request, path_args)

            for middleware in self.middleware.post_dispatch:
                resource = middleware(request, resource)

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

        # Encode the response
        try:
            return create_response(request, resource, status, headers)
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
