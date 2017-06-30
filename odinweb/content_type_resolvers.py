# -*- coding: utf-8 -*-
"""
Content Type Resolves
~~~~~~~~~~~~~~~~~~~~~

Collection of methods for resolving the content type of a request.

These methods are designed to work with either Flask or Bottle.

"""


def accepts_header():
    """
    Resolve content type from the accepts header.
    """
    def inner(request):
        return request.headers.get('accepts')
    return inner


def content_type_header():
    """
    Resolve content type from the content-type header.
    """
    def inner(request):
        return request.headers.get('content-type')
    return inner


class DefaultString(str):
    """
    Wrapper around a string to mark it as a default string.
    """
    is_default = True


def specific_default(content_type):
    """
    Specify a specific default content type.
    
    :param content_type: The content type to use.

    """
    def inner(_):
        return DefaultString(content_type)
    return inner

