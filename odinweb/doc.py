"""
Documentation Decorators
~~~~~~~~~~~~~~~~~~~~~~~~

Additional decorators for improving documentation of APIs.

"""
from collections import defaultdict
from typing import Any
from odin.utils import getmeta
from odinweb.utils import dict_filter, dict_filter_update

from . import _compat
from .constants import In, HTTPStatus

__all__ = (
    # Docs
    'OperationDoc', 'operation',
    'query_param', 'path_param', 'body', 'header_param',
    'response', 'produces'
)


class OperationDoc(object):
    """
    Utility class for building/storing documentation on callback endpoints.
    """

    #################################################################
    # Responses

    def add_response(self, status, description, resource=None):
        if isinstance(status, HTTPStatus):
            status = status.value

        self.responses[status] = dict_filter(
            description=description,
            schema={'$ref': '#/definitions/{}'.format(getmeta(resource).resource_name)} if resource else None
        )


def operation(summary=None, tags=None, deprecated=False):
    """
    Decorator for applying operation documentation to a callback.

    The values are based off `Swagger <https://swagger.io/specification>`_.

    """
    def inner(func):
        docs = OperationDoc.bind(func)
        docs.summary = summary
        docs.tags.update(tags)
        docs.deprecated = deprecated
        return func
    return inner


def query_param(name, type, description=None, required=False, default=None,
                minimum=None, maximum=None, enum=None, **options):
    """
    Query parameter documentation.
    """
    def inner(func):
        OperationDoc.bind(func).query_param(
            name, type, description, required, default, minimum, maximum, enum, **options
        )
        return func
    return inner


def path_param(name, type, description=None, default=None, minimum=None,
               maximum=None, enum=None, **options):
    """
    Path parameter documentation.
    """
    def inner(func):
        OperationDoc.bind(func).path_param(
            name, type, description, default, minimum, maximum, enum, **options
        )
        return func
    return inner


def body(description=None, default=None, **options):
    """
    Body parameter documentation. 
    """
    def inner(func):
        OperationDoc.bind(func).body_param(description, default, **options)
        return func
    return inner


def header_param(name, type, description=None, default=None, required=False, **options):
    """
    Header parameter documentation. 
    """
    def inner(func):
        OperationDoc.bind(func).header_param(name, type, description, default, required, **options)
        return func
    return inner


def response(status, description, resource=None):
    """
    Define an expected responses.

    The values are based off `Swagger <https://swagger.io/specification>`_.

    """
    def inner(func):
        OperationDoc.bind(func).add_response(status, description, resource)
        return func
    return inner


def produces(*content_types):
    """
    Define content types produced by an endpoint.
    """
    if not all(isinstance(content_type, _compat.string_types) for content_type in content_types):
        raise ValueError("In parameter not a valid value.")

    def inner(func):
        OperationDoc.bind(func).produces.update(content_types)
        return func
    return inner
