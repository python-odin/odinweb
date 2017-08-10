import datetime
import enum

from odin import fields

__all__ = ('HTTPStatus', 'Method', 'PathType', 'In', 'Type')

try:
    from http import HTTPStatus
except ImportError:
    from odinweb._compat.http import HTTPStatus


class Method(enum.Enum):
    """
    Well known HTTP methods (defined in Swagger Spec)
    """
    GET = 'GET'
    PUT = 'PUT'
    POST = 'POST'
    DELETE = 'DELETE'
    OPTIONS = 'OPTIONS'
    HEAD = 'HEAD'
    PATCH = 'PATCH'
    TRACE = 'TRACE'


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
    def __new__(cls, value, format_, native_type, odin_field):
        obj = str.__new__(cls, value)
        obj._value_ = value

        obj.format = format_
        obj.native_type = native_type
        obj.odin_field = odin_field
        return obj

    Integer = "integer", "int32", int, fields.IntegerField
    Long = "integer", "int64", int, fields.IntegerField
    Float = "number", "float", float, fields.FloatField
    Double = "number", "double", float, fields.FloatField
    String = "string", None, str, fields.StringField
    Byte = "string", "byte", bytes, fields.StringField
    Binary = "string", "binary", bytes, fields.StringField
    Boolean = "boolean", None, bool, fields.BooleanField
    Date = "string", "date", datetime.date, fields.DateField
    Time = "string", "time", datetime.time, fields.TimeField   # Not standard part of Swagger
    DateTime = "string", "date-time", datetime.datetime, fields.DateTimeField
    Password = "string", "password", str, fields.StringField


PATH_STRING_RE = r'[-\w.~,!%]+'
"""
Regular expression for a "string" in a URL path.

This includes all `Unreserved Characters <https://tools.ietf.org/html/rfc3986#section-2.3>`_ 
from URL Syntax RFC as well as a selection of sub-delims from 
`Reserved Characters <https://tools.ietf.org/html/rfc3986#section-2.2>`_.

"""
