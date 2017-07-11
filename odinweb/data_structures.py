from collections import namedtuple


# Used to define path nodes
PathNode = namedtuple('PathNode', 'name type type_args')
PathNode.__new__.__defaults__ = (None, None, None)

# Generic definition for a route to an API endpoint
ApiRoute = namedtuple("ApiRoute", 'path methods callback')


class HttpResponse(object):
    """
    Simplified HTTP response
    """
    __slots__ = ('status', 'body', 'headers')

    def __init__(self, body, status=200, headers=None):
        self.body = body
        self.status = status
        self.headers = headers or {}

    def __getitem__(self, item):
        return self.headers[item]

    def __setitem__(self, key, value):
        self.headers[key] = value

    def set_content_type(self, value):
        self.headers['content-type'] = value
