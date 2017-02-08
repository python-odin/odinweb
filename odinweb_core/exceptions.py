# -*- coding: utf-8 -*-
"""
Exceptions
~~~~~~~~~~

"""
from __future__ import unicode_literals
from odinweb_core.resources import Error


class ImmediateHttpResponse(Exception):
    """
    A response that should be returned immediately.
    """
    def __init__(self, resource, status=200, headers=None):
        self.resource = resource
        self.status = status
        self.headers = headers


class ImmediateErrorHttpResponse(ImmediateHttpResponse):
    """
    An error response that should be returned immediately.
    """
    def __init__(self, status, code, message, developer_message=None, meta=None, headers=None):
        super(ImmediateErrorHttpResponse, self).__init__(
            Error(status, code, message, developer_message, meta),
            status, headers
        )


class PermissionDenied(ImmediateErrorHttpResponse):
    """
    Permission has been denied.
    """
    def __init__(self, message=None, developer_message=None, headers=None):
        message = message or "Permission denied"
        super(PermissionDenied, self).__init__(403, 40300, message, developer_message, None, headers)
