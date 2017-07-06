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
        url_table = OrderedDict()
        route_table = {}

        for route_ in self._routes:
            route_number, path_type, methods, action_name, view = route_
            route_key = "%s-%s" % (path_type, action_name) if action_name else path_type

            # Populate url_table
            if route_key not in url_table:
                if path_type == PATH_TYPE_COLLECTION:
                    regex = action_name or r''
                else:
                    if action_name:
                        regex = r'(?P<resource_id>%s)/%s' % (self.resource_id_regex, action_name)
                    else:
                        regex = r'(?P<resource_id>%s)' % self.resource_id_regex

                url_table[route_key] = self.url(regex, self.wrap_view(route_key))

            # Populate route table
            method_map = route_table.setdefault(route_key, {})
            for method in methods:
                method_map[method] = view

            # Add options
            if self.respond_to_options:
                method_map.setdefault(constants.OPTIONS, 'options_response')

        # Store the route table at the same time
        self.route_table = dict(route_table)
        return list(url_table.values())

        # for func in self._routes:
        #     route_ = func.route  # type: RouteDefinition
        #     url_path = [self.api_name]
        #     if route_.path_type == constants.PATH_TYPE_RESOURCE:
        #         url_path.append(PathNode('resource_id', self.resource_id_type, None))
        #     if route_.sub_path:
        #         url_path += route_.sub_path
        #
        #     yield ApiRoute(route_.route_number, url_path, )
        #
        # return self._routes

    def get_paths(self):
        """
        Return the individual route paths
        """
        for route_ in self.routes:
            assert isinstance(route_, ApiRoute)

            if route_.path_type == constants.PATH_TYPE_COLLECTION:
                url_path = route_.sub_path or []
            else:
                url_path = [PathNode('resource_id', self.resource_id_type, None)]
                if route_.sub_path:
                    url_path += route_.sub_path

            route_key = '/'.join(url_path)

    def resolve_request_type(self, request):
        """
        Resolve the request content-type from the request object.
        """
        for resolver in self.request_type_resolvers:
            content_type = resolver(request)
            if content_type:
                return content_type

    def request_response_type(self, request):
        """
        Resolve the response content-type from the request object.
        """
        for resolver in self.response_type_resolvers:
            content_type = resolver(request)
            if content_type:
                return content_type

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

    def view(self, request):

        # Determine the request and response types. Ensure API supports the requested types
        request_type = self.resolve_request_type(request)
        response_type = self.resolve_response_type(request)
        try:
            request.request_codec = self.registered_codecs[request_type]
            request.response_codec = response_codec = self.registered_codecs[response_type]
        except KeyError:
            return 406, "Content cannot be returned in the format requested"

        try:
            result = self.dispatch_to_view(f, request)

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
                route_number, path, methods, callback = api_route
                yield ApiRoute(route_number, chain(path_prefix, api_route.path), methods, callback)

        if hasattr(self, 'additional_routes'):
            for api_route in self.additional_routes():
                route_number, path, methods, callback = api_route
                yield ApiRoute(route_number, chain(path_prefix, api_route.path), methods, callback)


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
            yield path, api_route.methods, api_route.callback

    def parse_node(self, node):
        raise NotImplementedError()
