import enum
try:
    from http import HTTPStatus
except ImportError:
    from odinweb._compat.http import HTTPStatus


class Method(enum.Enum):
    """
    Well known HTTP methods
    """
    Get = 'GET'
    Put = 'PUT'
    Head = 'HEAD'
    Post = 'POST'
    Patch = 'PATCH'
    Delete = 'DELETE'
    Options = 'OPTIONS'


# Type of path
class PathType(enum.Enum):
    Collection = 'collection'
    Resource = 'resource'


# Parameter location
class In(enum.Enum):
    Path = 'path'
    Query = 'query'
    Header = 'header'
    Body = 'body'
    Form = 'formData'


# Data-types
class Type(enum.Enum):
    String = "string"
    Number = "number"
    Integer = "integer"
    Boolean = "boolean"
    Array = "array"
    File = "file"
