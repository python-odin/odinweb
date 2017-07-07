"""
API
~~~

"""
from __future__ import absolute_import, unicode_literals

import logging
import sys

from collections import OrderedDict
from itertools import chain

from odin.codecs import json_codec
from odin.exceptions import ValidationError, CodecDecodeError
from odin.utils import getmeta

from . import _compat
from . import content_type_resolvers
from .data_structures import ApiRoute, PathNode
from .exceptions import ImmediateHttpResponse, ImmediateErrorHttpResponse
from .resources import Error

# Import all to simplify end user API.
from .constants import *  # noqa
from .decorators import *  # noqa

logger = logging.getLogger(__name__)

CODECS = {json_codec.CONTENT_TYPE: json_codec}
# Attempt to load other codecs that have dependencies
try:
    from odin.codecs import msgpack_codec
except ImportError:
    pass
else:
    CODECS[msgpack_codec.CONTENT_TYPE] = msgpack_codec


def resolve_content_type(type_resolvers, request):
    """
    Resolve content types from a request.
    """
    for resolver in type_resolvers:
        content_type = resolver(request)
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
        routes = sorted(routes, key=lambda o: o.route_number)

        # Get routes from parent objects
        for parent in parents:
            if hasattr(parent, 'routes'):
                routes.extend(parent.routes)

        attrs['_routes'] = routes

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

    respond_to_options = True
    """
    Respond to an options request.
    """

    parent = None

    def __init__(self):
        if not hasattr(self, 'api_name'):
            self.api_name = "{}".format(getmeta(self.resource).name)

        self._route_table = None  # type: dict

    @property
    def debug_enabled(self):
        """
        Is debugging enabled?
        """
        if self.parent:
            return self.parent.debug_enabled
        return False

    def _test_callback(self, request, **path_args):
        return "Response: {}\n{}\n{}".format(request.path, path_args, request.method)

    def api_routes(self):
        """
        Return implementation independent routes 
        """
        api_routes = []
        for route_ in self._routes:
            path = [self.api_name]
            if route_.path_type == PATH_TYPE_RESOURCE:
                path.append(PathNode('resource_id', self.resource_id_type, None))
            if route_.sub_path:
                path += route_.sub_path

            api_routes.append(ApiRoute(path, route_.methods, self._wrap_callback(route_.callback, route_.methods)))

        return api_routes

    def _wrap_callback(self, callback, methods):
        def wrapper(request, **path_args):
            if request.method not in methods:
                allow = ','.join(methods)
                raise ImmediateErrorHttpResponse(405, 40500, "Method not allowed",
                                                 headers={'Allow': allow}, meta={'allow': allow})

            # Determine the request and response types. Ensure API supports the requested types
            request_type = resolve_content_type(self.request_type_resolvers, request)
            response_type = resolve_content_type(self.response_type_resolvers, request)
            try:
                request.request_codec = self.registered_codecs[request_type]
                request.response_codec = response_codec = self.registered_codecs[response_type]
            except KeyError:
                return 406, "Content cannot be returned in the format requested"

            try:
                result = self.dispatch(callback, request, **path_args)

            except ImmediateHttpResponse as e:
                # An exception used to return a response immediately, skipping any
                # further processing.
                status = e.status
                resource = e.resource

            except ValidationError as e:
                # A validation error was raised by a resource.
                status = 400
                if hasattr(e, 'message_dict'):
                    resource = Error(status, status * 100, "Failed validation", meta=e.message_dict)
                else:
                    resource = Error(status, status * 100, str(e))

            except NotImplementedError:
                status = 501
                resource = Error(status, status * 100, "The method has not been implemented")

            except Exception as e:
                if self.debug_enabled:
                    # If debug is enabled then fallback to the frameworks default
                    # error processing, this often provides convenience features
                    # to aid in the debugging process.
                    raise
                resource = self.handle_500(request, e)
                status = resource.status

            else:
                if isinstance(result, tuple) and len(result) == 2:
                    resource, status = result
                else:
                    resource = result
                    # Return No Content status if result is None
                    status = 204 if result is None else 200

            if resource is None:
                return status, None
            else:
                return status, response_codec.dumps(resource)

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

        result = callback(request, **path_args)

        # Allow for a post_dispatch hook, the response of which is returned
        if hasattr(self, 'post_dispatch'):
            self.post_dispatch(request, result)
        else:
            return result

    def handle_500(self, request, exception):
        """
        Handle an *un-handled* exception.
        """
        exc_info = sys.exc_info()

        if self.debug_enabled:
            import traceback
            return Error(500, 50000, "An unhandled error has been caught.",
                         str(exception), traceback.format_exception(*exc_info))
        else:
            logger.error('Internal Server Error: %s', request.path, exc_info=exc_info, extra={
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

    def resource_from_body(self, request, allow_multiple=False, resource=None):
        """
        Get a resource instance from ``request.body``.
        """
        resource = resource or self.resource

        try:
            body = self.decode_body(request)
        except UnicodeDecodeError as ude:
            raise ImmediateErrorHttpResponse(400, 40099, "Unable to decode request body.", str(ude))

        try:
            resource = request.request_codec.loads(body, resource=resource, full_clean=False)

        except ValueError as ve:
            raise ImmediateErrorHttpResponse(400, 40098, "Unable to load resource.", str(ve))

        except CodecDecodeError as cde:
            raise ImmediateErrorHttpResponse(400, 40096, "Unable to decode body.", str(cde))

        # Check an array of data hasn't been supplied
        if not allow_multiple and isinstance(resource, list):
            raise ImmediateErrorHttpResponse(400, 40097, "Expected a single resource not a list.")

        return resource


class ApiCollection(object):
    """
    A collection of API endpoints
    """
    def __init__(self, *endpoints, **options):
        self.endpoints = endpoints

        self.name = options.pop('name', None)
        path_prefix = options.pop('path_prefix', None)
        if not path_prefix:
            path_prefix = [self.name] if self.name else []
        self.path_prefix = path_prefix

    def api_routes(self):
        path_prefix = self.path_prefix

        for endpoint in self.endpoints:
            for api_route in endpoint.api_routes():
                yield ApiRoute(chain(path_prefix, api_route.path), api_route.methods, api_route.callback)

        if hasattr(self, 'additional_routes'):
            for api_route in self.additional_routes():
                yield ApiRoute(chain(path_prefix, api_route.path), api_route.methods, api_route.callback)


class ApiVersion(ApiCollection):
    """
    Collection that defines a version.
    """
    def __init__(self, *endpoints, **options):
        options.setdefault('name', 'v1')
        super(ApiVersion, self).__init__(*endpoints, **options)


class ApiBase(ApiCollection):
    """
    Base class for API interface
    """
    def __init__(self, *endpoints, **options):
        options.setdefault('name', 'api')
        self.url_prefix = options.pop('url_prefix', '/')
        super(ApiBase, self).__init__(*endpoints, **options)

    def _build_routes(self):
        parse_node = self.parse_node
        # Ensure URL's start with a slash
        path_prefix = (self.url_prefix.strip('/ '), )

        for api_route in self.api_routes():
            path = '/'.join(parse_node(p) for p in chain(path_prefix, api_route.path))
            yield ApiRoute(path, api_route.methods, api_route.callback)

    def parse_node(self, node):
        raise NotImplementedError()
