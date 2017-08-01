"""
Testing Helpers
~~~~~~~~~~~~~~~

Collection of Mocks and Tools for testing APIs.

"""
from odin.codecs import json_codec

from odinweb.constants import Method


class MockRequest(object):
    """
    Mocked Request object
    """
    def __init__(self, query=None, post=None, headers=None, method=Method.GET, body='', host='127.0.0.1',
                 request_codec=None, response_codec=None):
        self.GET = query or {}
        self.POST = post or {}
        self.headers = headers or {}
        self.method = method
        self.body = body
        self.host = host
        self.request_codec = request_codec or json_codec
        self.response_codec = response_codec or json_codec
