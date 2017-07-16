"""
Documentation Decorators
~~~~~~~~~~~~~~~~~~~~~~~~

Additional decorators for improving documentation of APIs.

"""
from odin.utils import getmeta
from odinweb.utils import dict_filter, dict_filter_update

from . import _compat
from .constants import *

__all__ = (
    # Docs
    'OperationDoc', 'operation',
    'query_param', 'body_param', 'path_param', 'header_param',
    'response', 'produces'
)


class ResourceApiDoc(object):
    @classmethod
    def bind(cls, obj):
        # type: (object) -> ResourceApiDoc
        docs = getattr(obj, '__docs__', None)
        if docs is None:
            docs = cls(obj)
            setattr(obj, '__docs__', docs)
        return docs

    __slots__ = ('resource_api',)

    def __init__(self, resource_api):
        self.resource_api = resource_api


class OperationDoc(object):
    """
    Utility class for building/storing documentation on callback endpoints.
    """
    @classmethod
    def bind(cls, func):
        # type: (func) -> cls
        docs = getattr(func, '_api_docs', None)
        if docs is None:
            docs = cls(func)
            setattr(func, '_api_docs', docs)
        return docs

    __slots__ = ('callback', 'summary', 'tags', 'consumes', 'produces', 'parameters', 'responses', 'deprecated')

    def __init__(self, callback):
        self.callback = callback
        self.deprecated = None
        self.parameters = {}
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

    def add_parameter(self, name, in_, **options):
        # Ensure there are no duplicates
        param = self.parameters.setdefault("{}:{}".format(in_, name), {'name': name, 'in': in_})
        dict_filter_update(param, options)

    def body_param(self, resource, description=None, default=None, **options):
        """
        Set the body param
        """
        schema = {'$ref': '#/definitions/{}'.format(getmeta(resource).resource_name)} if resource else None
        self.add_parameter('body', In.Body.value, description=description, schema=schema, default=default, **options)

    def add_response(self, status, description, resource=None):
        response_spec = {'description': description}
        if resource:
            response_spec['schema'] = {'$ref': '#/definitions/{}'.format(getmeta(resource).resource_name)}

        self.responses[status] = response_spec

    def to_dict(self):
        return dict_filter(
            operationId=self.callback.__name__,
            description=(self.callback.__doc__ or '').strip(),
            deprecated=True if self.deprecated else None,
            parameters=self.parameters.values() if self.parameters else None,
            responses=self.responses if self.responses else None,
            produces=list(self.produces) if self.produces else None,
            tags=list(self.tags) if self.tags else None,
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


def query_param(name, type, description=None, required=False,
                default=None, minimum=None, maximum=None, enum=None, **options):
    """
    Query parameter documentation. 
    
    :param name: 
    :param type: 
    :param description: 
    :param required: 
    :param default:
    :param minimum:
    :param maximum:
    :param enum:

    """
    def inner(func):
        OperationDoc.bind(func).add_parameter(
            name, In.Query.value, type=type.value, description=description, required=required or None,
            default=default, minimum=minimum, maximum=maximum, enum=enum, **options)
        return func
    return inner


def path_param(name, type, description=None,
               default=None, minimum=None, maximum=None, enum=None, **options):
    """
    Path parameter documentation. 
    
    :param name: 
    :param type: 
    :param description: 
    :param default: 
    :param minimum: 
    :param maximum: 
    :param enum: 
    :param options: 

    """
    def inner(func):
        OperationDoc.bind(func).add_parameter(
            name, In.Path.value, type=type.value, description=description,
            default=default, minimum=minimum, maximum=maximum, enum=enum, **options
        )
        return func
    return inner


def body(resource=None, description=None, default=None, **options):
    """
    Body parameter documentation. 
    
    :param resource: 
    :param description: 
    :param default: 
    :param options: 

    """
    def inner(func):
        OperationDoc.bind(func).body_param(resource, description, default, **options)
        return func
    return inner


def header_param(name, type, description=None, required=False, **options):
    """
    Header parameter documentation. 

    :param name: 
    :param type: 
    :param description: 
    :param required:
    :param options: 

    """
    def inner(func):
        OperationDoc.bind(func).add_parameter(
            name, In.Query.value, type=type.value, description=description, required=required or None,
            **options)
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
