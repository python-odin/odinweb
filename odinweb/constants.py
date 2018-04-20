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


class Type(enum.Enum):
    """
    API Data type definitions
    """
    def __new__(cls, type_, format_, native_type, odin_field):
        value = "{}:{}".format(type_, format_) if format_ else type_

        obj = object.__new__(cls)
        obj._value_ = value  # noqa

        obj.type = type_
        obj.format = format_
        obj.native_type = native_type
        obj.odin_field = odin_field
        return obj

    def __str__(self):
        return self.type

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
    Email = "string", "email", str, fields.EmailField   # Not standard part of Swagger
    Regex = "string", "regex", str, fields.StringField   # Not standard part of Swagger


PATH_STRING_RE = r'[-\w.~,!%]+'
"""
Regular expression for a "string" in a URL path.

This includes all `Unreserved Characters <https://tools.ietf.org/html/rfc3986#section-2.3>`_ 
from URL Syntax RFC as well as a selection of sub-delims from 
`Reserved Characters <https://tools.ietf.org/html/rfc3986#section-2.2>`_.

"""

# Headers for CORS

CORS_ALLOW_CREDENTIALS = 'Access-Control-Allow-Credentials'
CORS_ALLOW_HEADERS = 'Access-Control-Allow-Headers'
CORS_ALLOW_METHODS = 'Access-Control-Allow-Methods'
CORS_ALLOW_ORIGIN = 'Access-Control-Allow-Origin'
CORS_EXPOSE_HEADERS = 'Access-Control-Expose-Headers'
CORS_MAX_AGE = 'Access-Control-Max-Age'
