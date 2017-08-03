"""
Testing Helpers
~~~~~~~~~~~~~~~

Collection of Mocks and Tools for testing APIs.

"""
from typing import Dict, Any

from odin.codecs import json_codec
try:
    from urllib.parse import urlparse, parse_qs
except ImportError:
    from urlparse import urlparse, parse_qs

from odinweb.constants import Method


class MockRequest(object):
    """
    Mocked Request object.

    This can be treated as a template of a request
    """
    @classmethod
    def from_uri(cls, uri, post=None, headers=None, method=Method.GET, body='',
                 request_codec=None, response_codec=None):
        # type: (str, Dict[str, str], Dict[str, str], Method, str, Any, Any) -> MockRequest
        scheme, netloc, path, params, query, fragment = urlparse(uri)
        query = {k: v[0] for k, v in parse_qs(query).items()}  # Hack need to use a multi dict.
        return cls(scheme, netloc, path, query, post, headers, method, body, request_codec, response_codec)

    def __init__(self, scheme='http', host='127.0.0.1', path=None, query=None, headers=None, method=Method.GET,
                 post=None, body='', request_codec=None, response_codec=None):
        # type: (str, str, str, Dict[str, str], Dict[str, str], Dict[str, str], Method, str, Any, Any) -> MockRequest
        self.scheme = scheme
        self.host = host
        self.path = path
        self.GET = query or {}
        self.headers = headers or {}
        self.method = method
        self.POST = post or {}
        self.body = body
        self.request_codec = request_codec or json_codec
        self.response_codec = response_codec or json_codec
