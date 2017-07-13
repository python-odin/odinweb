"""
Utils
~~~~~

Utility functions used to perform common operations.

"""
from __future__ import absolute_import, unicode_literals

import os
import base64
import itertools

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


def dict_filter_update(base, updates):
    # type: (dict, dict) -> None
    """
    Update dict with None values filtered out.
    
    :param base: 
    :param updates: 
     
    """
    base.update((k, v) for k, v in updates.items() if v is not None)


def dict_update_values(*args, **kwargs):
    """
    Merge into a dict with all of the None values removed.
    
    :param args: 
    :param kwargs:
    :rtype: dict
 
    """
    result = {}
    for arg in itertools.chain(args, (kwargs,)):
        dict_filter_update(result, arg)
    return result
