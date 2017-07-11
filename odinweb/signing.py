# -*- coding: utf-8 -*-
"""
Signing
~~~~~~~

Implementation of URL signing. 

"""
import hashlib
import hmac
import time

try:
    from urllib.parse import urlencode, urlparse, parse_qs
    from urllib.error import URLError
except ImportError:
    from urllib import urlencode
    from urllib2 import URLError
    from urlparse import parse_qs, urlparse

from ._compat import *
from .utils import random_string

DEFAULT_DIGEST = hashlib.sha256


def sign_url_path(url, secret_key, expire_in=None, digest=None):
    """
    Sign a URL (excluding the domain and scheme).

    :param url: URL to sign
    :param secret_key: Secret key
    :param expire_in: Expiry time.
    :param digest: Specify the digest function to use; default is sha256 from hashlib
    :return: Signed URL

    """
    result = urlparse(url)
    query_args = {k: v[0] for k, v in parse_qs(result.query).items()}

    query_args['_'] = random_string()
    if expire_in is not None:
        query_args['expires'] = int(time.time() + expire_in)
    query_args['signature'] = _generate_signature(result.path, secret_key, query_args, digest)

    return "%s?%s" % (result.path, urlencode(query_args))


def verify_url(url, secret_key, **kwargs):
    """
    Verify a signed URL (excluding the domain and scheme).

    :param url: URL to sign
    :param secret_key: Secret key
    :rtype: bool
    :raises: URLError

    """
    result = urlparse(url)
    query_args = {k: v[0] for k, v in parse_qs(result.query).items()}
    return verify_url_path(result.path, secret_key, query_args, **kwargs)


def verify_url_path(url_path, secret_key, query_args, salt_arg=None, max_expiry=None, digest=None):
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
        raise URLError("Signature missing.")

    if salt_arg is not None and salt_arg not in query_args:
        raise URLError("No salt provided.")

    if max_expiry is not None and 'expires' not in query_args:
        raise URLError("Expiry time is required.")

    # Validate signature
    signature = _generate_signature(url_path, secret_key, query_args, digest)
    if not hmac.compare_digest(signature, supplied_signature):
        raise URLError('Signature not valid.')

    # Check expiry
    try:
        expiry_time = int(query_args.pop('expires'))
    except KeyError:
        pass  # URL doesn't have an expire time
    except ValueError:
        raise URLError("Invalid expiry value.")
    else:
        expiry_delta = expiry_time - time.time()
        if expiry_delta < 0:
            raise URLError("Signature has expired")
        if expiry_delta > max_expiry:
            raise URLError("Expiry time out of range.")

    return True


def _generate_signature(url_path, secret_key, query_args, digest=None):
    """
    Generate signature from pre-parsed URL.
    """
    digest = digest or DEFAULT_DIGEST
    msg = "%s?%s" % (url_path, '&'.join('%s=%s' % (k, query_args[k]) for k in sorted(query_args)))
    return hmac.new(secret_key, msg, digestmod=digest).hexdigest()
