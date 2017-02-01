"""
Py27
~~~~

Even though Lambda only officially supports Python 2.7 this library is being developed Python 3.x first. This module
provides Python 2.7 fall-backs where possible.

This library assumes Python 2.7 if the version is less than 3.

"""
from __future__ import unicode_literals
import sys

__all__ = (
    'PY2', 'PY3',
    'string_types', 'integer_types', 'text_type', 'binary_type',
    'range'
)

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
    integer_types = int,
    text_type = str
    binary_type = bytes
else:
    string_types = basestring,
    integer_types = (int, long)
    text_type = unicode
    binary_type = str

if PY2:
    range = xrange
else:
    range = range
