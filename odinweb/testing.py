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
from .data_structures import MultiValueDict, BaseHttpRequest

# Typing
from .decorators import Operation  # noqa


def _prepare_mapping(mapping=None):
    # type: (dict) -> MultiValueDict
    mapping = mapping or {}
    return MultiValueDict((k.upper().replace('-', '_'), v) for k, v in mapping.items())


class MockRequest(BaseHttpRequest):
    """
    Mocked Request object.

    This can be treated as a template of a request
    """
    @classmethod
    def from_uri(cls, uri, headers=None, method=Method.GET, body='', form=None, environ=None,
                 cookies=None, session=None, request_codec=None, response_codec=None, current_operation=None):
        # type: (str, dict, Method, str, dict, dict, dict, Any, Any, Operation) -> MockRequest
        scheme, netloc, path, _, query, _ = urlparse(uri)
        return cls(scheme, netloc, path, parse_qs(query), headers, method, body, form,
                   environ, cookies, session, request_codec, response_codec, current_operation)

    def __init__(self, scheme='http', host='127.0.0.1', path=None, query=None, headers=None,
                 method=Method.GET, body='', form=None, environ=None, cookies=None, session=None,
                 request_codec=None, response_codec=None, current_operation=None):
        # type: (str, str, str, dict, dict, Method, str, dict, dict, dict, dict, Any, Any, Operation) -> None
        self._environ = _prepare_mapping(environ)
        self._method = method
        self._scheme = scheme
        self._host = host
        self._path = path or ''
        self._query = MultiValueDict(query or {})
        self._headers = _prepare_mapping(headers)
        self._cookies = MultiValueDict(cookies or {})
        self._session = MultiValueDict(session or {})
        self._body = body
        self._form = MultiValueDict(form or {})

        self.request_codec = request_codec or json_codec
        self.response_codec = response_codec or json_codec
        self.current_operation = current_operation

    @property
    def environ(self):
        return self._environ

    @property
    def method(self):
        return self._method

    @property
    def scheme(self):
        return self._scheme

    @property
    def host(self):
        return self._host

    @property
    def path(self):
        return self._path

    @property
    def query(self):
        return self._query

    @property
    def headers(self):
        return self._headers

    @property
    def cookies(self):
        return self._cookies

    @property
    def session(self):
        return self._session

    @property
    def body(self):
        return self._body

    @property
    def form(self):
        return self._form
