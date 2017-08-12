"""
Utils
~~~~~

Utility functions used to perform common operations.

"""
from __future__ import absolute_import

import os
import base64
import itertools

# Typing imports
from typing import Any  # noqa

from . import _compat


if _compat.PY2:
    def token(bit_depth=64, encoder=base64.b32encode):
        """
        Generate a random token of a certain bit depth and strip any padding.
        """
        # Fast divide by 8 ;)
        chars = bit_depth >> 3
        if bit_depth == chars << 3:
            return encoder(os.urandom(chars)).rstrip('=')
        raise ValueError("Bit depth must be a multiple of 8")
else:
    def token(bit_depth=64, encoder=base64.b32encode):
        """
        Generate a random token of a certain bit depth and strip any padding.
        """
        # Fast divide by 8 ;)
        chars = bit_depth >> 3
        if bit_depth == chars << 3:
            data = os.urandom(chars)
            return encoder(data).decode().rstrip('=')
        raise ValueError("Bit depth must be a multiple of 8")


def to_bool(value):
    # type: (Any) -> bool
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


def dict_filter(*args, **kwargs):
    """
    Merge all values into a single dict with all None values removed.
    
    :param args: 
    :param kwargs:
    :rtype: dict
 
    """
    result = {}
    for arg in itertools.chain(args, (kwargs,)):
        dict_filter_update(result, arg)
    return result


def sort_by_priority(iterable, reverse=False, default_priority=10):
    """
    Return a list or objects sorted by a priority value.
    """
    return sorted(iterable, reverse=reverse, key=lambda o: getattr(o, 'priority', default_priority))
