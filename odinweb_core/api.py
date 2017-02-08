"""
API
~~~

"""
from __future__ import absolute_import, unicode_literals

import logging
import six
import sys

from collections import namedtuple
from odin.codecs import json_codec
from odin.exceptions import ValidationError, CodecDecodeError
from odin.utils import getmeta

from . import content_type_resolvers
from .exceptions import ImmediateHttpResponse, ImmediateErrorHttpResponse
from .resources import Error

__all__ = ('ResourceApi', 'ApiCollection', 'ApiVersion', 'Api')

CODECS = {json_codec.CONTENT_TYPE: json_codec}
logger = logging.getLogger(__name__)

ApiRoute = namedtuple("ApiRoute", ('route_number', 'path_type', 'method', 'action_name', 'view'))


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
                routes.append(ApiRoute(*obj.route, view=view))
                del obj.route
        routes = sorted(routes, key=lambda o: o.route_number)

        # Get routes from parent objects
        for parent in parents:
            if hasattr(parent, 'routes'):
                routes.extend(parent.routes)

        attrs['routes'] = routes

        return super_new(mcs, name, bases, attrs)


class ResourceApi(six.with_metaclass(ResourceApiMeta)):
    """
    Base framework specific ResourceAPI implementations.
    """
    resource = None
    """
    The resource this API is modelled on.
    """
    resource_id_regex = r'\d+'

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
    url_prefix = r''

    debug_enabled = False
    respond_to_options = True

    def __init__(self, api_name=None):
        if api_name:
            self.api_name = api_name
        elif not hasattr(self, 'api_name'):
            self.api_name = "{}s".format(getmeta(self.resource).name)

        # The parent api object (if within an API collection)
        self.parent = None

    @property
    def debug_enabled(self):
        """
        Is debugging enabled?
        """
        if self.parent:
            return self.parent.debug_enabled
        return False

    def api_rules(self):
        rules = []
        for route in self.routes:
            pass

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
    A collection of several resource APIs
    """
    def __init__(self, *resource_apis, **kwargs):
        self.api_name = kwargs.pop('api_name', 'api')
        self.resource_apis = resource_apis

    def api_rules(self):
        pass


class ApiVersion(ApiCollection):
    """
    A versioned collection of resource APIs
    """
    def __init__(self, *resource_apis, **kwargs):
        kwargs.setdefault('api_name', kwargs.pop('version', 'v1'))
        super(ApiVersion, self).__init__(*resource_apis, **kwargs)


class Api(object):
    """
    An API made up of several API versions.

    >>> api = Api(
    ...     ApiVersion(
    ...         UserApi(),
    ...         MyApi()
    ...     )
    ... )

    """
    def __init__(self, *versions, **kwargs):
        self.versions = versions
        self.api_name = kwargs.pop('api_name', 'api')

    def get_routes(self):
        """
        Get a list of routes defined by the API.
        """
        routes = []
