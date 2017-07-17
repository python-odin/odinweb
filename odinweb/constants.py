import enum

try:
    from http import HTTPStatus
except ImportError:
    from odinweb._compat.http import HTTPStatus


class Method(enum.Enum):
    """
    Well known HTTP methods
    """
    GET = 'GET'
    PUT = 'PUT'
    HEAD = 'HEAD'
    POST = 'POST'
    PATCH = 'PATCH'
    DELETE = 'DELETE'
    OPTIONS = 'OPTIONS'


class PathType(enum.Enum):
    """
    Type of path to use
    """
    Collection = 'collection'
    Resource = 'resource'


class In(enum.Enum):
    """
    Location of a parameter
    """
    Path = 'path'
    Query = 'query'
    Header = 'header'
    Body = 'body'
    Form = 'formData'


class Type(enum.Enum):
    """
    API Data type definitions
    """
    String = "string"
    Number = "number"
    Integer = "integer"
    Boolean = "boolean"
    Array = "array"
    File = "file"
