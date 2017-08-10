import base64
import pytest

from odinweb.data_structures import UrlPath
from odinweb.decorators import Operation
from odinweb.exceptions import PermissionDenied
from odinweb.middleware import signing
from odinweb.testing import MockRequest


class TestSignedAuth(object):
    @pytest.mark.parametrize('uri', (
        "/foo/bar?_=YJEYWGBKGUVZS&signature=QKUNPLEDOMFVU2NBTEASPR2J4B524KFMG4GMW2NJISVG2RQQVJEA",
        "/foo/bar?a=1&b=2&_=YJEYWGBKGUVZS&signature=TU773VE25K5UFPHV6DGD5NXT7D74SFZYKVMEB6ZRONK2UXHT72EQ",
    ))
    def test_valid_signature(self, uri):
        request = MockRequest.from_uri(uri)

        target = signing.FixedSignedAuth(base64.b32decode('DEADBEEF'))

        @Operation(path=UrlPath.parse('/foo/bar'), middleware=[target])
        def callback(r):
            return 'ok'

        actual = callback(request, {})

        assert actual == 'ok'

    def test_no_key(self):
        request = MockRequest.from_uri('/foo/bar')

        target = signing.FixedSignedAuth(None)

        @Operation(path=UrlPath.parse('/foo/bar'), middleware=[target])
        def callback(request):
            return 'ok'

        with pytest.raises(PermissionDenied):
            callback(request, {})

    @pytest.mark.parametrize('url, kwargs', (
        # Signature missing
        ("/foo/bar?_=YJEYWGBKGUVZS", {}),
        # No salt_used
        ("/foo/bar?_=YJEYWGBKGUVZS&signature=QKUNPLEDOMFVU2NBTEASPR2J4B524KFMG4GMW2NJISVG2RQQVJEA", {'salt_arg': 'x'}),
        # Expiry time is required.
        ("/foo/bar?_=YJEYWGBKGUVZS&signature=QKUNPLEDOMFVU2NBTEASPR2J4B524KFMG4GMW2NJISVG2RQQVJEA", {'max_expiry': 10}),
        # Signature not valid.
        ("/foo/bar?_=YJEYWGBKGUVZS&signature=QKUNPLEDOMFVU2NBTEASPR2J4B524KFMG4GMW2NJISVG2RQQVJED", {}),
        # Invalid expiry value
        ("/foo/bar?signature=LZ7DKPFZ3UTQB3OCABLOMGDXNKAS4GFM5PNFECZV7FHQF5MXFZFQ&expires=zz&_=YJEYWGBKGUVZS", {}),
    ))
    def test_error(self, url, kwargs):
        request = MockRequest.from_uri('/foo/bar')

        target = signing.FixedSignedAuth(base64.b32decode('DEADBEEF'))

        @Operation(path=UrlPath.parse('/foo/bar'), middleware=[target])
        def callback(request):
            return 'ok'

        with pytest.raises(PermissionDenied):
            callback(request, {})


