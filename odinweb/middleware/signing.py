"""
Middleware utilising URL signing for authentication.
"""
from __future__ import absolute_import

import logging

# Typing imports
from typing import Callable  # noqa

from .. import signing
from ..exceptions import PermissionDenied, SigningError

logger = logging.getLevelName(__name__)


class SignedAuthBase(object):
    """
    Middleware to verify a signed request.
    """
    priority = 3  # Ensure authentication run early

    def __init__(self, salt_arg='_', max_expiry=None, digest=None):
        # type: (str, int, Callable) -> None
        self.salt_arg = salt_arg
        self.max_expiry = max_expiry
        self.digest = digest

    def get_secret_key(self, request, path_args):
        """
        Hook to fetch set secret key or allow a secret key to be obtained storage.
        
        Note!
        
        If a user/account or similar object cannot be found you should return `None`. This will
        cause a :class:`odinweb.exceptions.PermissionDenied` exception with a generic message to
        be raised so as not to leak information about the validity or a user/account identifier.
        
        """
        raise NotImplementedError

    def pre_dispatch(self, request, path_args):
        """
        Pre dispatch hook
        """
        secret_key = self.get_secret_key(request, path_args)
        if not secret_key:
            raise PermissionDenied('Signature not valid.')

        try:
            signing.verify_url_path(request.path, request.GET, secret_key)
        except SigningError as ex:
            raise PermissionDenied(str(ex))


class FixedSignedAuth(SignedAuthBase):
    """
    Signed auth middleware that uses a fixed secret key.

    Using a fixed secret key is not recommended.

    """
    def __init__(self, secret_key, *args, **kwargs):
        # type: (bytes, *str, **str) -> None
        super(FixedSignedAuth, self).__init__(*args, **kwargs)
        self.secret_key = secret_key

    def get_secret_key(self, request, path_args):
        return self.secret_key
