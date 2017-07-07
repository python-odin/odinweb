# -*- coding: utf-8 -*-
"""
Exceptions
~~~~~~~~~~

"""
from odinweb.resources import Error


class ImmediateHttpResponse(Exception):
    """
    A response that should be returned immediately.
    """
    def __init__(self, resource, status=200, headers=None):
        self.resource = resource
        self.status = status
        self.headers = headers


class HttpError(ImmediateHttpResponse):
    """
    An error response that should be returned immediately.
    """
    def __init__(self, status, code, message, developer_message=None, meta=None, headers=None):
        super(HttpError, self).__init__(
            Error(status, code, message, developer_message, meta),
            status, headers
        )


class PermissionDenied(HttpError):
    """
    Permission to access the specified resource is denied.
    """
    def __init__(self, message=None, developer_method=None, headers=None):
        super(PermissionDenied, self).__init__(
            403, 40300, message or "Permission Denied",
            developer_method, None, headers
        )
