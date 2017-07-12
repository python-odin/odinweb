"""
Documentation Decorators
~~~~~~~~~~~~~~~~~~~~~~~~

Additional decorators for improving documentation of APIs.

"""
from odin.utils import getmeta

from . import _compat
from .constants import *

__all__ = (
    # Docs
    'OperationDoc', 'operation', 'parameter', 'response', 'produces'
)


class OperationDoc(object):
    """
    Utility class for building/storing documentation on callback endpoints.
    """
    @classmethod
    def get(cls, func):
        docs = getattr(func, '_api_docs', None)
        if docs is None:
            docs = cls(func)
            setattr(func, '_api_docs', docs)
        return docs

    __slots__ = 'callback _parameters summary deprecated tags responses produces'.split()

    def __init__(self, callback):
        self.callback = callback
        self.summary = None
        self.deprecated = False
        self.tags = set()
        self._parameters = {}
        self.responses = {
            'default': {
                'description': 'Error',
                'schema': {'$ref': '#/definitions/Error'}
            }
        }
        self.produces = set()

    def add_parameter(self, name, in_, **options):
        # Ensure there are no duplicates
        param = self._parameters.setdefault("{}:{}".format(in_, name), {})
        param['name'] = name
        param['in'] = in_
        param.update((k, v) for k, v in options.items() if v is not None)

    def add_response(self, status, description, resource=None):
        response_spec = {'description': description}
        if resource:
            response_spec['schema'] = {'$ref': '#/definitions/{}'.format(getmeta(resource).resource_name)}

        self.responses[status] = response_spec

    @property
    def parameters(self):
        return list(self._parameters.values())

    @property
    def description(self):
        return self.callback.__doc__.strip()

    def to_dict(self):
        d = {
            "operationId": self.callback.__name__,
            "description": (self.callback.__doc__ or '').strip(),
        }
        if self.deprecated:
            d['deprecated'] = True
        if self.produces:
            d['produces'] = list(self.produces)
        if self.tags:
            d['tags'] = list(self.tags)
        if self.responses:
            d['responses'] = self.responses
        if self.parameters:
            d['parameters'] = self.parameters

        return d


def operation(summary=None, tags=None, deprecated=False):
    """
    Decorator for applying operation documentation to a callback.

    The values are based off `Swagger <https://swagger.io/specification>`_.

    """
    def inner(func):
        docs = OperationDoc.get(func)
        docs.summary = summary
        docs.tags.update(tags)
        docs.deprecated = deprecated
        return func
    return inner


def parameter(name, in_, required=None, type_=None, default=None):
    """
    Decorator for applying parameter documentation to a callback.

    The values are based off `Swagger <https://swagger.io/specification>`_.

    """
    if in_ not in In:
        raise ValueError("In parameter not a valid value.")

    def inner(func):
        OperationDoc.get(func).add_parameter(name, in_.value, required=required, type=type_.value, default=default)
        return func
    return inner


def body_param(resource=None, description=None):
    """
    Decorator for defining request body
    """
    def inner(func):
        args = {
            'description': description,
        }
        if resource:
            args['schema'] = {'$ref': '#/definitions/{}'.format(getmeta(resource).resource_name)}
        OperationDoc.get(func).add_parameter('', In.Body.value, **args)
        return func
    return inner


def response(status, description, resource=None):
    """
    Define an expected responses.

    The values are based off `Swagger <https://swagger.io/specification>`_.

    """
    def inner(func):
        OperationDoc.get(func).add_response(status, description, resource)
        return func
    return inner


def produces(*content_types):
    """
    Define content types produced by an endpoint.
    """
    if not all(isinstance(content_type, _compat.string_types) for content_type in content_types):
        raise ValueError("In parameter not a valid value.")

    def inner(func):
        OperationDoc.get(func).produces.update(content_types)
        return func
    return inner
