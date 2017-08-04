"""
Facebook contrib
~~~~~~~~~~~~~~~~

Helpers for handing requests from Facebook.

"""
import hashlib
import hmac

from odinweb.exceptions import PermissionDenied


class XHubSignatureMiddleware(object):
    """
    Middleware to validate a Facebook X-Hub-Signature header.
    """
    priority = 5

    def __init__(self, app_key):
        # type: (str) -> None
        self.app_key = app_key

    def pre_dispatch(self, request, _):
        """
        Handle pre-dispatch event
        """
        signature = "sha1=" + hmac.new(self.app_key, request.body, hashlib.sha1).hexdigest()
        if signature != request.headers.get(''):
            raise PermissionDenied("Invalid signature")
