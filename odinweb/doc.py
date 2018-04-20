"""
Documentation Decorators
~~~~~~~~~~~~~~~~~~~~~~~~

Additional decorators for improving documentation of APIs.

"""
# Included for type support
from typing import Callable, Optional  # noqa
from odin import Resource  # noqa
from .constants import HTTPStatus  # noqa
from .data_structures import Param  # noqa

from . import _compat
from .data_structures import Response, DefaultResource

__all__ = ('deprecated', 'add_param', 'response', 'produces')


def deprecated(operation=None):
    """
    Mark an operation deprecated.
    """
    def inner(o):
        o.deprecated = True
        return o
    return inner(operation) if operation else inner


def add_param(param):
    # type: (Param) -> Callable
    """
    Add parameter, you should probably use on of :meth:`path_param`, :meth:`query_param`,
    :meth:`body_param`, or :meth:`header_param`.
    """
    def inner(o):
        try:
            getattr(o, 'parameters').add(param)
        except AttributeError:
            setattr(o, 'parameters', {param})
        return o
    return inner


def response(status, description, resource=DefaultResource):
    # type: (HTTPStatus, str, Optional[Resource]) -> Callable
    """
    Define an expected response.

    The values are based off `Swagger <https://swagger.io/specification>`_.

    """
    def inner(o):
        value = Response(status, description, resource)
        try:
            getattr(o, 'responses').add(value)
        except AttributeError:
            setattr(o, 'responses', {value})
        return o
    return inner


def produces(*content_types):
    """
    Define content types produced by an endpoint.
    """
    def inner(o):
        if not all(isinstance(content_type, _compat.string_types) for content_type in content_types):
            raise ValueError("In parameter not a valid value.")
        try:
            getattr(o, 'produces').update(content_types)
        except AttributeError:
            setattr(o, 'produces', set(content_types))
        return o
    return inner
