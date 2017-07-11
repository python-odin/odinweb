import enum


# Well known methods
GET = 'GET'
HEAD = 'HEAD'
POST = 'POST'
PUT = 'PUT'
PATCH = 'PATCH'
DELETE = 'DELETE'
OPTIONS = 'OPTIONS'


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
