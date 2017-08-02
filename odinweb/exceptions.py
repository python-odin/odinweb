# -*- coding: utf-8 -*-
"""
Exceptions
~~~~~~~~~~

"""
from .constants import HTTPStatus
from .resources import Error

__all__ = ('ImmediateHttpResponse', 'HttpError', 'PermissionDenied', 'AccessDenied')


class ImmediateHttpResponse(Exception):
    """
    A response that should be returned immediately.
    """
    def __init__(self, resource, status=HTTPStatus.OK, headers=None):
        self.resource = resource
        self.status = status
        self.headers = headers


class HttpError(ImmediateHttpResponse):
    """
    An error response that should be returned immediately.
    """
    def __init__(self, status, code_index=0, message=None, developer_message=None, meta=None, headers=None):
        super(HttpError, self).__init__(
            Error.from_status(status, code_index, message, developer_message, meta), status, headers
        )


class PermissionDenied(HttpError):
    """
    Authorization is required before making this request.
    """
    def __init__(self, message=None, developer_method=None, headers=None):
        super(PermissionDenied, self).__init__(HTTPStatus.UNAUTHORIZED, 0, message, developer_method, None, headers)


class AccessDenied(HttpError):
    """
    Access to the specified resource is denied.
    """
    def __init__(self, message=None, developer_method=None, headers=None):
        super(AccessDenied, self).__init__(HTTPStatus.FORBIDDEN, 0, message, developer_method, None, headers)


class SigningError(Exception):
    """
    Error raised during a signing operation
    """
