"""
Utils
~~~~~

Utility functions used to perform common operations.

"""
from __future__ import absolute_import, unicode_literals

import os
import base64


def random_string(bit_depth=64):
    """
    Generate a random string of a certain bit depth
    """
    assert (bit_depth % 8) == 0, "Bit depth must be a multiple of 8"
    return base64.urlsafe_b64encode(os.urandom(bit_depth/8))
