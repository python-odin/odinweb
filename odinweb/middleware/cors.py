from odinweb import api
from odinweb.utils import dict_filter
from odinweb.exceptions import ImmediateHttpResponse

# Imports for typing support
from typing import Optional, Any, Sequence, Tuple, Dict, Union  # noqa
from odinweb.data_structures import HttpResponse  # noqa


class AnyOrigin(object):
    pass


class CORS(object):
    """
    CORS (Cross-Origin Request Sharing) support for OdinWeb APIs.

    See `MDN documentation <https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS>`_
    for a technical description of CORS.

    :param origin_whitelist: List of whitelisted origins or use `AnyOrigin` to
        return a '*' or allow all.
    :param max_age: Max length of time access control headers can be cached
        in seconds. `None`, disables this header; a value of -1 will disable
        caching, requiring a preflight *OPTIONS* check for all calls.
    :param expose_headers: Request headers can be access by a client beyond
        the simple headers, *Cache-Control*, *Content-Language*,
        *Content-Type*, *Expires*, *Last-Modified*, *Pragma*.
    :param allow_headers: Headers that are allowed to be sent by the browser
        beyond the simple headers, *Accept*, *Accept-Language*,
        *Content-Language*, *Content-Type*.

    """
    priority = 1

    def __init__(self, origin_whitelist, max_age=None, expose_headers=None, allow_headers=None):
        # type: (Union[Sequence[str], AnyOrigin], Optional[int], Sequence[str], Sequence[str]) -> None
        self.origin_whitelist = origin_whitelist
        self.max_age = max_age
        self.expose_headers = expose_headers
        self.allow_headers = allow_headers

    def origin_components(self, request):
        # type: (Any) -> Tuple[str, str]
        """
        Return URL components that make up the origin.

        This allows for customisation in the case or custom headers/proxy
        configurations.

        :return: Tuple consisting of Scheme, Host/Port

        """
        return request.scheme, request.host

    def allow_credentials(self, request):
        # type: (Any) -> Optional[bool]
        """
        Generate allow credential header

        Returning `None` prevents the header being sent.

        """
        return None

    def allow_methods(self, request):
        # type: (Any) -> Sequence[str]
        """
        Generate list of allowed methods.
        """
        return [m.value for m in request.current_operation.methods]

    def allow_origin(self, request):
        # type: (Any) -> str
        """
        Generate allow origin header
        """
        origin_whitelist = self.origin_whitelist
        if origin_whitelist is AnyOrigin:
            return '*'
        else:
            origin = "{}://{}".format(*self.origin_components(request))
            return origin if origin in origin_whitelist else ''

    def option_headers(self, request):
        # type: (Any) -> Dict[str, str]
        """
        Generate option headers.
        """
        return dict_filter({
            'Access-Control-Allow-Origin': self.allow_origin(request),
            'Access-Control-Allow-Methods': ', '.join(self.allow_methods(request)),
            'Access-Control-Allow-Credentials': {True: 'true', False: 'false'}.get(self.allow_credentials(request)),
            'Access-Control-Allow-Headers': self.allow_headers,
            'Access-Control-Expose-Headers': self.expose_headers,
            'Access-Control-Max-Age': str(self.max_age) if self.max_age else None,
            'Cache-Control': 'no-cache, no-store'
        })

    def response_headers(self, request):
        # type: (Any) -> Dict[str, str]
        """
        Generate response headers.
        """
        return dict_filter({
            'Access-Control-Allow-Methods': ', '.join(self.allow_methods(request)),
        })

    def pre_request(self, request, _):
        # type: (Any, Any) -> None
        """
        Pre-request hook to check for an Options request and to prepare CORS
        headers.
        """
        if request.method == api.Method.OPTIONS:
            raise ImmediateHttpResponse(None, headers=self.option_headers(request))

    def post_request(self, request, response):
        # type: (Any, HttpResponse) -> HttpResponse
        """
        Post-request hook to allow CORS headers to responses.
        """
        if request.method != api.Method.OPTIONS:
            response.headers['Access-Control-Allow-Origin'] = self.allow_origin(request)
        return response
