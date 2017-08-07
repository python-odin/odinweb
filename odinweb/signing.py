# -*- coding: utf-8 -*-
"""
Signing
~~~~~~~

Implementation of URL signing. 

"""
import base64
import hashlib
import hmac

from odinweb.data_structures import MultiValueDict
from time import time
try:
    from urllib.parse import urlencode, urlparse, parse_qs
except ImportError:
    from urllib import urlencode
    from urlparse import parse_qs, urlparse

# Type imports
from typing import Callable, Dict  # noqa

from . import _compat
from .exceptions import SigningError
from .utils import token

DEFAULT_DIGEST = hashlib.sha256
DEFAULT_ENCODER = base64.b32encode


def _generate_signature(url_path, secret_key, query_args, digest=None, encoder=None):
    # type: (str, bytes, Dict[str, str], Callable, Callable) -> str
    """
    Generate signature from pre-parsed URL.
    """
    digest = digest or DEFAULT_DIGEST
    encoder = encoder or DEFAULT_ENCODER
    msg = "%s?%s" % (url_path, '&'.join('%s=%s' % i for i in query_args.sorteditems(multi=True)))
    if _compat.text_type:
        msg = msg.encode('UTF8')
    signature = hmac.new(secret_key, msg, digestmod=digest).digest()
    if _compat.PY2:
        return encoder(signature).rstrip('=')  # Strip padding
    else:
        return encoder(signature).decode().rstrip('=')  # Strip padding


def sign_url_path(url, secret_key, expire_in=None, digest=None):
    # type: (str, bytes, int, Callable) -> str
    """
    Sign a URL (excluding the domain and scheme).

    :param url: URL to sign
    :param secret_key: Secret key
    :param expire_in: Expiry time.
    :param digest: Specify the digest function to use; default is sha256 from hashlib
    :return: Signed URL

    """
    result = urlparse(url)
    query_args = MultiValueDict(parse_qs(result.query))
    query_args['_'] = token()
    if expire_in is not None:
        query_args['expires'] = int(time() + expire_in)
    query_args['signature'] = _generate_signature(result.path, secret_key, query_args, digest)
    return "%s?%s" % (result.path, urlencode(list(query_args.sorteditems(True))))


def verify_url_path(url_path, query_args, secret_key, salt_arg='_', max_expiry=None, digest=None):
    # type: (str, Dict[str, str], bytes, str, int, Callable) -> bool
    """
    Verify a URL path is correctly signed.

    :param url_path: URL path
    :param secret_key: Signing key
    :param query_args: Arguments that make up the query string
    :param salt_arg: Argument required for salt (set to None to disable)
    :param max_expiry: Maximum length of time an expiry value can be for (set to None to disable)
    :param digest: Specify the digest function to use; default is sha256 from hashlib
    :rtype: bool
    :raises: URLError

    """
    try:
        supplied_signature = query_args.pop('signature')
    except KeyError:
        raise SigningError("Signature missing.")

    if salt_arg is not None and salt_arg not in query_args:
        raise SigningError("No salt used.")

    if max_expiry is not None and 'expires' not in query_args:
        raise SigningError("Expiry time is required.")

    # Validate signature
    signature = _generate_signature(url_path, secret_key, query_args, digest)
    if not hmac.compare_digest(signature, supplied_signature):
        raise SigningError('Signature not valid.')

    # Check expiry
    try:
        expiry_time = int(query_args.pop('expires'))
    except KeyError:
        pass  # URL doesn't have an expire time
    except ValueError:
        raise SigningError("Invalid expiry value.")
    else:
        expiry_delta = expiry_time - time()
        if expiry_delta < 0:
            raise SigningError("Signature has expired.")
        if max_expiry and expiry_delta > max_expiry:
            raise SigningError("Expiry time out of range.")

    return True


def verify_url(url, secret_key, **kwargs):
    """
    Verify a signed URL (excluding the domain and scheme).

    :param url: URL to sign
    :param secret_key: Secret key
    :rtype: bool
    :raises: URLError

    """
    result = urlparse(url)
    query_args = MultiValueDict(parse_qs(result.query))
    return verify_url_path(result.path, query_args, secret_key, **kwargs)
