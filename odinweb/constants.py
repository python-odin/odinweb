import enum

from odin import fields

__all__ = ('HTTPStatus', 'Method', 'PathType', 'In', 'Type')

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


class Type(str, enum.Enum):
    """
    API Data type definitions
    """
    def __new__(cls, value, native_type, odin_field):
        obj = str.__new__(cls, value)
        obj._value_ = value

        obj.native_type = native_type
        obj.odin_field = odin_field
        return obj

    String = "string", str, fields.StringField
    Number = "number", float, fields.FloatField
    Integer = "integer", int, fields.IntegerField
    Boolean = "boolean", bool, fields.BooleanField
    # Array = "array", list, fields.ListField
    # File = "file", str, fields.StringField
