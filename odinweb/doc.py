"""
Documentation Decorators
~~~~~~~~~~~~~~~~~~~~~~~~

Additional decorators for improving documentation of APIs.

"""
from odin.utils import getmeta

from . import _compat
from .constants import In, HTTPStatus
from .data_structures import Param
from .utils import dict_filter, make_decorator

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


def query_param(*args, **kwargs):
    """
    Query parameter documentation.
    """
    return add_param(Param.query(*args, **kwargs))


def path_param(*args, **kwargs):
    """
    Path parameter documentation.
    """
    return add_param(Param.path(*args, **kwargs))


def body(*args, **kwargs):
    """
    Body parameter documentation. 
    """
    return add_param(Param.body(*args, **kwargs))


def header_param(*args, **kwargs):
    """
    Header parameter documentation. 
    """
    return add_param(Param.header(*args, **kwargs))


@make_decorator
def response(operation, status, description, resource=None):
    """
    Define an expected responses.

    The values are based off `Swagger <https://swagger.io/specification>`_.

    """
    if isinstance(status, HTTPStatus):
        status = status.value

    data = getattr(operation, 'responses', None)
    if not data:
        data = {}
        setattr(operation, 'responses', data)

    data[status] = dict_filter(
        description=description,
        schema={'$ref': '#/definitions/{}'.format(getmeta(resource).resource_name)} if resource else None
    )


@make_decorator
def produces(operation, *content_types):
    """
    Define content types produced by an endpoint.
    """
    if not all(isinstance(content_type, _compat.string_types) for content_type in content_types):
        raise ValueError("In parameter not a valid value.")

    data = getattr(operation, 'produces', None)
    if not data:
        data = set()
        setattr(operation, 'produces', data)

    data.update(content_types)
