from __future__ import absolute_import

from . import api
from .data_structures import HttpResponse, UrlPath
from .utils import dict_filter

# Imports for typing support
from typing import Optional, Any, Sequence, Tuple, Dict, Union, List, Type  # noqa
from .containers import ApiInterfaceBase  # noqa


class AnyOrigin(object):
    pass


Origins = Union[Sequence[str], Type[AnyOrigin]]


class CORS(object):
    """
    CORS (Cross-Origin Request Sharing) support for OdinWeb APIs.

    See `MDN documentation <https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS>`_
    for a technical description of CORS.

    :param origins: List of whitelisted origins or use `AnyOrigin` to return a
        '*' or allow all.
    :param max_age: Max length of time access control headers can be cached
        in seconds. `None`, disables this header; a value of -1 will disable
        caching, requiring a pre-flight *OPTIONS* check for all calls.
    :param allow_credentials: Indicate that credentials can be submitted to
        this API.
    :param expose_headers: Request headers can be access by a client beyond
        the simple headers, *Cache-Control*, *Content-Language*,
        *Content-Type*, *Expires*, *Last-Modified*, *Pragma*.
    :param allow_headers: Headers that are allowed to be sent by the browser
        beyond the simple headers, *Accept*, *Accept-Language*,
        *Content-Language*, *Content-Type*.

    """
    priority = 1

    def __new__(cls, api_interface, *args, **kwargs):
        # type: (CORS, ApiInterfaceBase, *Any, **Any) -> ApiInterfaceBase
        instance = object.__new__(cls)
        instance.__init__(api_interface, *args, **kwargs)

        # Add instance as middleware
        api_interface.middleware.append(instance)

        return api_interface

    def __init__(self, api_interface, origins, max_age=None, allow_credentials=None,
                 expose_headers=None, allow_headers=None):
        # type: (ApiInterfaceBase, Origins, Optional[int], Optional[bool], Sequence[str], Sequence[str]) -> None
        self.origins = origins if origins is AnyOrigin else set(origins)
        self.max_age = max_age
        self.expose_headers = expose_headers
        self.allow_headers = allow_headers
        self.allow_credentials = allow_credentials

        self._register_options(api_interface)

    def _register_options(self, api_interface):
        # type: (ApiInterfaceBase) -> None
        """
        Register CORS options endpoints.
        """
        op_paths = api_interface.op_paths(collate_methods=True)
        for path, operations in op_paths.items():
            if api.Method.OPTIONS not in operations:
                self._options_operation(api_interface, path, operations.keys())

    def _options_operation(self, api_interface, path, methods):
        # type: (ApiInterfaceBase, UrlPath, List[api.Method]) -> None
        """
        Generate an options operation for the specified path
        """
        # Trim off path prefix.
        if path.startswith(api_interface.path_prefix):
            path = path[len(api_interface.path_prefix):]

        methods = set(methods)
        methods.add(api.Method.OPTIONS)

        @api_interface.operation(path, api.Method.OPTIONS)
        def _cors_options(request, **_):
            return HttpResponse(None, headers=self.option_headers(request, methods))

        _cors_options.operation_id = path.format(separator='.') + '.cors_options'

    def origin_components(self, request):
        # type: (Any) -> Tuple[str, str]
        """
        Return URL components that make up the origin.

        This allows for customisation in the case or custom headers/proxy
        configurations.

        :return: Tuple consisting of Scheme, Host/Port

        """
        return request.scheme, request.host

    def allow_origin(self, request):
        # type: (Any) -> str
        """
        Generate allow origin header
        """
        origins = self.origins
        if origins is AnyOrigin:
            return '*'
        else:
            origin = "{}://{}".format(*self.origin_components(request))
            return origin if origin in origins else ''

    def option_headers(self, request, methods):
        # type: (Any, Sequence[api.Method]) -> Dict[str, str]
        """
        Generate option headers.
        """
        return dict_filter({
            'Access-Control-Allow-Origin': self.allow_origin(request),
            'Access-Control-Allow-Methods': ', '.join(m.value for m in methods),
            'Access-Control-Allow-Credentials': {True: 'true', False: 'false'}.get(self.allow_credentials),
            'Access-Control-Allow-Headers': ', '.join(self.allow_headers) if self.allow_headers else None,
            'Access-Control-Expose-Headers': ', '.join(self.expose_headers) if self.expose_headers else None,
            'Access-Control-Max-Age': str(self.max_age) if self.max_age else None,
            'Cache-Control': 'no-cache, no-store'
        })

    def post_request(self, request, response):
        # type: (Any, HttpResponse) -> HttpResponse
        """
        Post-request hook to allow CORS headers to responses.
        """
        if request.method != api.Method.OPTIONS:
            response.headers['Access-Control-Allow-Origin'] = self.allow_origin(request)
        return response
