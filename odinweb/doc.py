"""
Documentation Decorators
~~~~~~~~~~~~~~~~~~~~~~~~

Additional decorators for improving documentation of APIs.

"""
from collections import defaultdict
from typing import Any

from odin.utils import getmeta

from . import _compat
from .constants import In, HTTPStatus
from .utils import dict_filter_update, dict_filter

__all__ = (
    'deprecated',
    'query_param', 'path_param', 'body', 'header_param',
    'response', 'produces'
)


def deprecated(operation=None):
    """
    Mark an operation deprecated.
    """
    def inner(func):
        func.deprecated = True
        return func
    return inner(operation) if operation else inner


def _add_param(name, in_, obj=None, **options):
    # type: (name, In, **Any) -> None
    """
    Add parameter, you should probably use on of :meth:`path_param`, :meth:`query_param`,
    :meth:`body_param`, or :meth:`header_param`.
    """
    def inner(func):
        data = getattr(func, '_parameters', None)
        if not data:
            data = defaultdict(lambda: defaultdict(dict))
            setattr(func, '_parameters', data)

        dict_filter_update(data[in_][name], options)

        return func
    return inner(obj) if obj else inner


def query_param(name, type, description=None, required=False, default=None,
                minimum=None, maximum=None, enum=None, **options):
    """
    Query parameter documentation.
    """
    return _add_param(name, In.Query, type=type, description=description,
                      minimum=minimum, maximum=maximum, enum=enum,
                      required=required, default=default, **options)


def path_param(name, type, description=None, default=None, minimum=None,
               maximum=None, enum=None, **options):
    """
    Path parameter documentation.
    """
    return _add_param(name, In.Path, type=type, description=description,
                      minimum=minimum, maximum=maximum, enum=enum,
                      default=default, **options)


def body(description=None, default=None, **options):
    """
    Body parameter documentation. 
    """
    return _add_param('body', In.Body, description=description,
                      default=default, **options)


def header_param(name, type, description=None, default=None, required=False, **options):
    """
    Header parameter documentation. 
    """
    return _add_param(name, In.Header, type=type, description=description,
                      required=required, default=default, **options)


def response(status, description, resource=None):
    """
    Define an expected responses.

    The values are based off `Swagger <https://swagger.io/specification>`_.

    """
    if isinstance(status, HTTPStatus):
        status = status.value

    def inner(func):
        data = getattr(func, 'responses', None)
        if not data:
            data = {}
            setattr(func, 'responses', data)

        data[status] = dict_filter(
            description=description,
            schema={'$ref': '#/definitions/{}'.format(getmeta(resource).resource_name)} if resource else None
        )

        return func
    return inner


def produces(*content_types):
    """
    Define content types produced by an endpoint.
    """
    if not all(isinstance(content_type, _compat.string_types) for content_type in content_types):
        raise ValueError("In parameter not a valid value.")

    def inner(func):
        data = getattr(func, 'produces', None)
        if not data:
            data = set()
            setattr(func, 'produces', data)

        data.update(content_types)

        return func
    return inner
