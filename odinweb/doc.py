"""
Documentation Decorators
~~~~~~~~~~~~~~~~~~~~~~~~

Additional decorators for improving documentation of APIs.

"""
from typing import Callable, Optional

from odin import Resource

from . import _compat
from .constants import HTTPStatus
from .data_structures import Param, Response, DefaultResource
from .utils import make_decorator

__all__ = (
    'deprecated',
    'query_param', 'path_param', 'body', 'header_param',
    'response', 'produces'
)


@make_decorator
def deprecated(operation):
    """
    Mark an operation deprecated.
    """
    operation.deprecated = True


@make_decorator
def add_param(operation, param):
    # type: (Param) -> None
    """
    Add parameter, you should probably use on of :meth:`path_param`, :meth:`query_param`,
    :meth:`body_param`, or :meth:`header_param`.
    """
    try:
        getattr(operation, 'parameters').append(param)
    except AttributeError:
        setattr(operation, 'parameters', {param})


@make_decorator
def response(operation, status, description, resource=DefaultResource):
    # type: (Callable, HTTPStatus, str, Optional[Resource]) -> None
    """
    Define an expected responses.

    The values are based off `Swagger <https://swagger.io/specification>`_.

    """
    value = Response(status, description, resource)

    try:
        getattr(operation, 'responses').update(value)
    except AttributeError:
        setattr(operation, 'responses', {value})


@make_decorator
def produces(operation, *content_types):
    """
    Define content types produced by an endpoint.
    """
    if not all(isinstance(content_type, _compat.string_types) for content_type in content_types):
        raise ValueError("In parameter not a valid value.")

    try:
        getattr(operation, 'produces').update(content_types)
    except AttributeError:
        setattr(operation, 'parameters', set(content_types))
