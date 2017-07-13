"""
Testing Helpers
~~~~~~~~~~~~~~~

Collection of Mocks and Tools for testing APIs.

"""


class MockRequest(object):
    """
    Mocked Request object
    """
    def __init__(self, query=None, post=None, headers=None, method='GET', body='', host='127.0.0.1'):
        self.GET = query or {}
        self.POST = post or {}
        self.headers = headers or {}
        self.method = method
        self.body = body
        self.host = host
