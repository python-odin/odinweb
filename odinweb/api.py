"""
API
~~~

"""
from __future__ import absolute_import, unicode_literals

import logging

from functools import wraps
from itertools import chain
from odin.codecs import json_codec
from odin.exceptions import ValidationError, CodecDecodeError
from odin.utils import getmeta

from . import _compat
from . import content_type_resolvers
from .data_structures import ApiRoute, PathNode, HttpResponse
from .exceptions import ImmediateHttpResponse, HttpError
from .resources import Error
from .utils import parse_content_type

# Import all to simplify end user API.
from .constants import *  # noqa
from .decorators import *  # noqa

logger = logging.getLogger(__name__)

CODECS = {
    json_codec.CONTENT_TYPE: json_codec,
}
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

        routes = []

        # Get local routes and sort them by route number
        for view, obj in attrs.items():
            if callable(obj) and hasattr(obj, 'route'):
                routes.append(obj.route)
                del obj.route

        # Get routes from parent objects
        for parent in parents:
            if hasattr(parent, '_routes'):
                routes.extend(parent._routes)

        attrs['_routes'] = sorted(routes, key=lambda o: o.route_number)

        return super_new(mcs, name, bases, attrs)


class ResourceApi(_compat.with_metaclass(ResourceApiMeta)):
    """
    Base framework specific ResourceAPI implementations.
    """
    resource = None
    """
    The resource this API is modelled on.
    """

    resource_id_type = 'int'
    """
    Resource ID type.
    """

    resource_id_name = 'resource_id'
    """
    Name of the resource ID field
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

    registered_codecs = CODECS
    """
    Codecs that are supported by this API.
    """

    remap_codecs = {
        'text/plain': 'application/json'
    }
    """
    Remap certain codecs commonly mistakenly used.
    """

    parent = None

    def __init__(self):
        if not hasattr(self, 'api_name'):
            self.api_name = "{}".format(getmeta(self.resource).name.lower())

        self._api_routes = None

    @property
    def debug_enabled(self):
        """
        Is debugging enabled?
        """
        if self.parent:
            return self.parent.debug_enabled
        return False

    def api_routes(self):
        """
        Return implementation independent routes 
        """
        if self._api_routes is None:
            api_routes = []
            for route_ in self._routes:
                path = [self.api_name]

                if route_.path_type == PathType.Resource:
                    path.append(PathNode(self.resource_id_name, self.resource_id_type, None))

                if route_.sub_path:
                    path += route_.sub_path

                api_routes.append(ApiRoute(path, route_.methods, self._wrap_callback(route_.callback, route_.methods)))
            self._api_routes = api_routes

        return self._api_routes

    def _wrap_callback(self, callback, methods):
        @wraps(callback)
        def wrapper(request, **path_args):
            # Determine the request and response types. Ensure API supports the requested types
            request_type = resolve_content_type(self.request_type_resolvers, request)
            request_type = self.remap_codecs.get(request_type, request_type)
            try:
                request.request_codec = self.registered_codecs[request_type]
            except KeyError:
                return HttpResponse("Un-supported body content.", 406)

            response_type = resolve_content_type(self.response_type_resolvers, request)
            response_type = self.remap_codecs.get(response_type, response_type)
            try:
                request.response_codec = self.registered_codecs[response_type]
            except KeyError:
                return HttpResponse("Un-supported response type.", 406)

            # Check if method is in our allowed method list
            if request.method not in methods:
                return HttpResponse("Method not allowed.", 405, {'Allow', ','.join(methods)})

            # Response types
            status = headers = None

            try:
                resource = self.dispatch(callback, request, **path_args)

            except ImmediateHttpResponse as e:
                # An exception used to return a response immediately, skipping any
                # further processing.
                resource, status, headers = e.resource, e.status, e.headers

            except ValidationError as e:
                # A validation error was raised by a resource.
                if hasattr(e, 'message_dict'):
                    resource = Error(400, 40000, "Failed validation", meta=e.message_dict)
                else:
                    resource = Error(400, 40000, str(e))
                status = resource.status

            except NotImplementedError:
                resource = Error(501, 50100, "The method has not been implemented")
                status = resource.status

            except Exception as e:
                if self.debug_enabled:
                    # If debug is enabled then fallback to the frameworks default
                    # error processing, this often provides convenience features
                    # to aid in the debugging process.
                    raise
                resource = self.handle_500(request, e)
                status = resource.status

            # Return a HttpResponse and just send it!
            if isinstance(resource, HttpResponse):
                return resource

            return self.create_response(request, resource, status, headers)

        return wrapper

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

    def handle_500(self, request, exception):
        """
        Handle an *un-handled* exception.
        """
        logger.exception('Internal Server Error: %s', exception, extra={
            'status_code': 500,
            'request': request
        })
        return Error(500, 50000, "An unhandled error has been caught.")

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
            raise HttpError(400, 40099, "Unable to decode request body.", str(ude))

        try:
            resource = request.request_codec.loads(body, resource=resource, full_clean=False)

        except ValueError as ve:
            raise HttpError(400, 40098, "Unable to load resource.", str(ve))

        except CodecDecodeError as cde:
            raise HttpError(400, 40096, "Unable to decode body.", str(cde))

        # Check an array of data hasn't been supplied
        if not allow_multiple and isinstance(resource, list):
            raise HttpError(400, 40097, "Expected a single resource not a list.")

        return resource

    def create_response(self, request, body=None, status=None, headers=None):
        """
        Generate a HttpResponse.
        
        :param request: Request object 
        :param body: Body of the response
        :param status: HTTP status code
        :param headers: Any headers.

        """
        if not body:
            return HttpResponse(None, status or 204, headers)

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
            return HttpResponse("Error encoding response.", 500)
        else:
            response = HttpResponse(body, status or 200, headers)
            response.set_content_type(request.response_codec.CONTENT_TYPE)
            return response


class ApiContainer(object):
    """
    Container or API endpoints.
    
    This class is intended as a base class for other API classes. Containers
    can also be nested. This is used to support versions etc.
    
    """
    def __init__(self, *endpoints, **options):
        self.endpoints = endpoints

        self.name = options.pop('name', None)
        path_prefix = options.pop('path_prefix', None)
        if not path_prefix:
            path_prefix = [self.name] if self.name else []
        self.path_prefix = path_prefix

        if options:
            raise TypeError("Got an unexpected keyword argument '{}'", options.keys()[-1])

    def api_routes(self, path_prefix=None):
        """
        Return all of the API routes defined the API endpoints in the container.
        """
        if path_prefix is None:
            path_prefix = self.path_prefix

        for endpoint in self.endpoints:
            endpoint.parent = self
            for api_route in endpoint.api_routes():
                yield ApiRoute(chain(path_prefix, api_route.path), *api_route[1:])

        if hasattr(self, 'additional_routes'):
            additional_routes = self.additional_routes
            if callable(additional_routes):
                additional_routes = additional_routes()

            for api_route in additional_routes:
                yield ApiRoute(chain(path_prefix, api_route.path), *api_route[1:])

    def referenced_resources(self):
        # type: () -> set
        """
        Return a set of resources referenced by the API.
        """
        resources = set()
        for endpoint in self.endpoints:
            if isinstance(endpoint, ResourceApi):
                # Add ResourceApi resource
                if endpoint.resource:
                    resources.add(endpoint.resource)

                # Add any route specific resources
                resources.update(r.callback.resource
                                 for r in endpoint.api_routes()
                                 if getattr(r.callback, 'resource', None))

            elif isinstance(endpoint, ApiContainer):
                resources.update(endpoint.referenced_resources())

        return resources


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
    def __init__(self, *endpoints, **options):
        self.version = options.pop('version', 1)
        options.setdefault('name', 'v{}'.format(self.version))
        super(ApiVersion, self).__init__(*endpoints, **options)


class ApiInterfaceBase(ApiContainer):
    """
    Base class for API interfaces. 
    
    API interfaces are the interfaces between OdinWeb and the web framework 
    being used.
    
    """
    def __init__(self, *endpoints, **options):
        options.setdefault('name', 'api')
        self.url_prefix = options.pop('url_prefix', '/')
        self.debug_enabled = options.pop('debug_enabled', False)
        super(ApiInterfaceBase, self).__init__(*endpoints, **options)

    def build_routes(self):
        parse_node = self.parse_node
        # Ensure URL's start with a slash
        path_prefix = (self.url_prefix.rstrip('/'),)

        for api_route in self.api_routes():
            path = '/'.join(parse_node(p) for p in chain(path_prefix, api_route.path))
            yield ApiRoute(path, api_route.methods, api_route.callback)

    def parse_node(self, node):
        raise NotImplementedError()
