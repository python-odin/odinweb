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
    def resolver(request):
        return request.headers.get('accepts')
    return resolver


def content_type_header():
    """
    Resolve content type from the content-type header.
    """
    def resolver(request):
        return request.headers.get('content-type')
    return resolver


def specific_default(content_type):
    """
    Specify a specific default content type.
    
    :param content_type: The content type to use.

    """
    def resolver(_):
        return content_type
    return resolver

