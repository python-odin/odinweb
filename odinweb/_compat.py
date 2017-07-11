# -*- coding: utf-8 -*-
"""
Py27 Support
~~~~~~~~~~~~

Like odin this library will support Python 2.7 through to a 2.0 release. From
this point onwards Python 3.5+ will be required.

"""
import sys

__all__ = (
    'PY2', 'PY3',
    'string_types', 'integer_types', 'text_type', 'binary_type',
    'range', 'with_metaclass'
)

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY2:
    string_types = basestring,
    integer_types = (int, long)
    text_type = unicode
    binary_type = str

    range = xrange
else:
    string_types = str,
    integer_types = int,
    text_type = str
    binary_type = bytes
    range = range

def with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    # This requires a bit of explanation: the basic idea is to make a dummy
    # metaclass for one level of class instantiation that replaces itself with
    # the actual metaclass.
    class metaclass(meta):
        def __new__(cls, name, this_bases, d):
            return meta(name, bases, d)
    return type.__new__(metaclass, 'temporary_class', (), {})
