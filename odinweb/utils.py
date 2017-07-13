"""
Utils
~~~~~

Utility functions used to perform common operations.

"""
from __future__ import absolute_import, unicode_literals

import os
import base64

from . import _compat


def random_string(bit_depth=64):
    """
    Generate a random string of a certain bit depth
    """
    assert (bit_depth % 8) == 0, "Bit depth must be a multiple of 8"
    return base64.urlsafe_b64encode(os.urandom(bit_depth/8))


def parse_content_type(value):
    # type: (str) -> str
    """
    Parse out the content type from a content type header.
    
    >>> parse_content_type('application/json; charset=utf8')
    'application/json'
    
    """
    if not value:
        return ''

    return value.split(';')[0].strip()


def to_bool(value):
    # type: (*) -> bool
    """
    Convert a value into a bool but handle "truthy" strings eg, yes, true, ok, y
    """
    if isinstance(value, _compat.string_types):
        return value.upper() in ('Y', 'YES', 'T', 'TRUE', '1', 'OK')
    return bool(value)


def first(iterable):
    """
    Return the first item in an iterable. If there are no items return None.
    """
    try:
        return next(iterable)
    except StopIteration:
        return


def find(function, iterable):
    """
    Return first item from an iterable for which function(item)
    is true. If function is None, return the first item that is true.
    """
    return first(filter(function, iterable))
