"""
Utils
~~~~~

Utility functions used to perform common operations.

"""
from __future__ import absolute_import

import os
import base64
import itertools
from functools import wraps

from typing import Any  # noqa

from . import _compat


def random_string(bit_depth=64):
    # type: (int) -> str
    """
    Generate a random string of a certain bit depth
    """
    if bit_depth % 8 != 0:
        raise ValueError("Bit depth must be a multiple of 8")
    return base64.urlsafe_b64encode(os.urandom(bit_depth/8)).rstrip('=')


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


def make_decorator(decorator):
    """
    Convert a function into a decorator.
    """
    @wraps(decorator)
    def wrapper(f=None, *args, **kwargs):
        def inner(func):
            return decorator(func, *args, **kwargs) or func
        if not callable(f):
            a = [f]
            a.extend(args)
            args, f = a, None
        return inner(f) if f else inner
    return wrapper
