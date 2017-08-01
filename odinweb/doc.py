"""
Documentation Decorators
~~~~~~~~~~~~~~~~~~~~~~~~

Additional decorators for improving documentation of APIs.

"""
# Included for type support
from typing import Callable, Optional  # noqa
from odin import Resource  # noqa

from . import _compat
from .constants import HTTPStatus
from .data_structures import Param, Response, DefaultResource
from .utils import make_decorator

__all__ = ('deprecated', 'add_param', 'response', 'produces')


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
        getattr(operation, 'parameters').add(param)
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
        getattr(operation, 'responses').add(value)
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
        setattr(operation, 'produces', set(content_types))
