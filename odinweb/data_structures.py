from collections import namedtuple

from .constants import *


# Used to define path nodes
PathNode = namedtuple('PathNode', 'name type type_args')
PathNode.__new__.__defaults__ = (None, Type.Integer, None)

# Generic definition for a route to an API endpoint
ApiRoute = namedtuple("ApiRoute", 'path methods operation')


class HttpResponse(object):
    """
    Simplified HTTP response
    """
    __slots__ = ('status', 'body', 'headers')

    @classmethod
    def from_status(cls, http_status, headers=None):
        # type: (HTTPStatus, **str) -> HttpResponse
        return cls(http_status.description or http_status.phrase, http_status, headers)

    def __init__(self, body, status=HTTPStatus.OK, headers=None):
        self.body = body
        if isinstance(status, HTTPStatus):
            status = status.value
        self.status = status
        self.headers = headers or {}

    def __getitem__(self, item):
        return self.headers[item]

    def __setitem__(self, key, value):
        self.headers[key] = value

    def set_content_type(self, value):
        self.headers['content-type'] = value
