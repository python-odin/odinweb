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
    @classmethod
    def bind(cls, func):
        # type: (func) -> cls
        docs = getattr(func, '__docs', None)
        if docs is None:
            docs = cls()
            setattr(func, '__docs', docs)
        docs.callback = func
        return docs

    __slots__ = ('callback', 'summary', 'tags', 'consumes', 'produces', '_parameters', 'responses', 'deprecated')

    def __init__(self):
        self.callback = None
        self.deprecated = None
        self._parameters = defaultdict(lambda: defaultdict(dict))
        self.responses = {
            'default': {
                'description': 'Error',
                'schema': {'$ref': '#/definitions/Error'}
            }
        }
        self.produces = set()
        self.consumes = {}
        self.summary = None
        self.tags = set()

    def to_dict(self, parent=None):
        return dict_filter(
            operationId=self.operation_id,
            description=self.description,
            deprecated=True if self.deprecated else None,
            parameters=self.parameters,
            responses=self.responses if self.responses else None,
            produces=list(self.produces) if self.produces else None,
            tags=list(self.tags) if self.tags else None,
        )

    @property
    def operation_id(self):
        return self.callback.__name__

    @property
    def description(self):
        return (self.callback.__doc__ or '').strip()

    @property
    def parameters(self):
        results = []

        for param_type in (In.Path, In.Header, In.Query, In.Form):
            results.extend(self._parameters[param_type].values())

        if In.Body in self._parameters:
            body_param = self._parameters[In.Body]
            resource = getattr(self.callback, 'resource', None)
            if resource:
                body_param['schema'] = {
                    '$ref': '#/definitions/{}'.format(getmeta(resource).resource_name)
                }
            results.append(body_param)

        return results or None

    #################################################################
    # Parameters

    def add_param(self, name, in_, **options):
        # type: (name, In, **Any) -> None
        """
        Add parameter, you should probably use on of :meth:`path_param`, :meth:`query_param`,
        :meth:`body_param`, or :meth:`header_param`.
        """
        dict_filter_update(self._parameters[in_][name], options)

    def path_param(self, name, type_, description=None,
                   default=None, minimum=None, maximum=None, enum_=None, **options):
        """
        Add Path parameter
        """
        self.add_param(
            name, In.Path, type=type_.value, description=description,
            default=default, minimum=minimum, maximum=maximum, enum=enum_,
            **options
        )

    def query_param(self, name, type_, description=None, required=False,
                    default=None, minimum=None, maximum=None, enum_=None, **options):
        """
        Add Query parameter
        """
        self.add_param(
            name, In.Query, type=type_.value, description=description,
            required=required or None, default=default, minimum=minimum, maximum=maximum, enum=enum_,
            **options
        )

    def body_param(self, description=None, default=None, **options):
        """
        Set the body param
        """
        self._parameters[In.Body] = dict_filter(
            {'name': 'body', 'in': In.Body.value, 'description': description, 'default': default},
            options
        )

    def header_param(self, name, type_, description=None, default=None, required=False, **options):
        """
        Add a header parameter
        """
        self.add_param(
            name, In.Header, type=type_.value, description=description, required=required or None,
            default=default,
            **options
        )

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
