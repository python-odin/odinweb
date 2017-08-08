"""
Testing Helpers
~~~~~~~~~~~~~~~

Collection of Mocks and Tools for testing APIs.

"""
from __future__ import absolute_import

from collections import MutableMapping
# Imports to support typing
from typing import Dict, Any  # noqa

from odin.codecs import json_codec
try:
    from urllib.parse import urlparse, parse_qs
except ImportError:
    from urlparse import urlparse, parse_qs

from .constants import Method
from .data_structures import MultiValueDict


class MockRequest(object):
    """
    Mocked Request object.

    This can be treated as a template of a request
    """
    @classmethod
    def from_uri(cls, uri, post=None, headers=None, method=Method.GET, body='',
                 request_codec=None, response_codec=None):
        # type: (str, Dict[str, str], Dict[str, str], Method, str, Any, Any) -> MockRequest
        scheme, netloc, path, _, query, _ = urlparse(uri)
        return cls(scheme, netloc, path, parse_qs(query), headers, method, post, body, request_codec, response_codec)

    def __init__(self, scheme='http', host='127.0.0.1', path=None, query=None, headers=None, method=Method.GET,
                 post=None, body='', request_codec=None, response_codec=None):
        # type: (str, str, str, Dict[str, str], MultiValueDict, Dict[str, str], Method, str, Any, Any) -> MockRequest
        self.scheme = scheme
        self.host = host
        self.path = path
        self.GET = MultiValueDict(query or {})
        self.headers = headers or {}
        self.method = method
        self.POST = MultiValueDict(post or {})
        self.body = body
        self.request_codec = request_codec or json_codec
        self.response_codec = response_codec or json_codec


def check_request_proxy(request_proxy):
    """
    A set of standard tests for Request Proxies.

    This is for use by integrations with python web frameworks to verify the request proxy
    behaves as expected.

    """
    for attr, expected_type in (
        ('scheme', str),
        ('host', str),
        ('path', None),
        ('GET', MultiValueDict),
        ('headers', (dict, MutableMapping)),
        ('method', Method),
        ('POST', MultiValueDict),
        ('body', None),
    ):
        assert hasattr(request_proxy, attr), "{} instance missing attribute {}.".format(request_proxy.__class__, attr)
        obj = getattr(request_proxy, attr)
        if expected_type:
            assert isinstance(obj, expected_type), "Incorrect type of {}.{}; expected {} got {}.".format(
                request_proxy.__class__, attr, expected_type, type(obj))
