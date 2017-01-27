# -*- coding: utf-8 -*-
import logging
import sys

from odin.codecs import json_codec
from odin.exceptions import ValidationError
from odin.utils import getmeta

from odinweb import content_type_resolvers
from odinweb.exceptions import ImmediateHttpResponse
from odinweb.resources import Error

CODECS = {json_codec.CONTENT_TYPE: json_codec}

logger = logging.getLogger("odinweb")


class ResourceApiBase(object):
    """
    Base framework specific ResourceAPI implimentations.
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
        Is debugging on?
        """
        if self.parent:
            return self.parent.debug_enabled
        return False

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

    def view(self, request):
        request_type = self.resolve_request_type(request)
        response_type = self.resolve_response_type(request)
        try:
            request_codec = self.registered_codecs[request_type]
            response_codec = self.registered_codecs[response_type]
        except KeyError:
            return 406, "Content cannot be returned in the format requested"

        try:
            result = self.dispatch_to_view(f, request)

        except ImmediateHttpResponse as e:
            # An exception used to return a response immediately, skipping any
            # further processing.
            pass
        
        except ValidationError as e:
            # A validation error was raised by a resource.
            status = 400
            if hasattr(e, 'message_dict'):
                resource = Error(status, status*100, "Failed validation", meta=e.message_dict)
            else:
                resource = Error(status, status*100, str(e))

        # except PermissionDenied as e:
        #     status = 403
        #     resource = Error(status, status*100, "Permission denied", str(e))

        except NotImplementedError:
            status = 501
            resource = Error(status, status*100, "The method has not been implemented")

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
            return "eek"
        else:
            return status, response_codec.dumps(resource)

