import base64

import pytest

from odinweb import signing


@pytest.mark.parametrize('url_path, kwargs, expected', (
    ('/foo/bar', {'query_args': {}},
     "XC6FH5OSR5KORFNMP4RGI5XVUJNYYKUL5VL374LP5E6LU4F2N66Q"),
    ('/foo/bar', {'query_args': {}, 'encoder': base64.b16encode},
     "B8BC53F5D28F54E895AC7F226476F5A25B8C2A8BED57BFF16FE93CBA70BA6FBD"),
    ('/foo/bar', {'query_args': {'a': '1', 'b': '2'}},
     "6T27IPZQWFBBQBIEQTP4HWSYZETFRLHZOKTLAPAKD3BV4SUMO2ZA"),
    ('/foo/bar', {'query_args': {'a': '1', 'b': '2'}, 'encoder': base64.b16encode},
     "F4F5F43F30B14218050484DFC3DA58C92658ACF972A6B03C0A1EC35E4A8C76B2"),
))
def test_generate_signature(url_path, kwargs, expected):
    kwargs.setdefault('secret_key', base64.b32decode('DEADBEEF'))
    actual = signing._generate_signature(url_path, **kwargs)
    assert actual == expected


@pytest.mark.parametrize('url, kwargs, expected', (
    ('/foo/bar', {},
     "/foo/bar?_=YJEYWGBKGUVZS&signature=QKUNPLEDOMFVU2NBTEASPR2J4B524KFMG4GMW2NJISVG2RQQVJEA"),
    ('https://www.savage.company/foo/bar', {},
     "/foo/bar?_=YJEYWGBKGUVZS&signature=QKUNPLEDOMFVU2NBTEASPR2J4B524KFMG4GMW2NJISVG2RQQVJEA"),
    ('https://www.savage.company/foo/bar?a=1&b=2', {},
     "/foo/bar?a=1&b=2&_=YJEYWGBKGUVZS&signature=TU773VE25K5UFPHV6DGD5NXT7D74SFZYKVMEB6ZRONK2UXHT72EQ"),
    ('https://www.savage.company/foo/bar?a=1&b=2', {'expire_in': 20},
     "/foo/bar?a=1&b=2&expires=1020&_=YJEYWGBKGUVZS&signature=XRKDRGPSUXFQUG36CNSOFY6RSWJFYSKTUOORJIQUUDG4WBCZOKUA"),
))
def test_sign_url_path(monkeypatch, url, kwargs, expected):
    # Monkey patch to fix token and time values.
    monkeypatch.setattr(signing, 'token', lambda: 'YJEYWGBKGUVZS')
    monkeypatch.setattr(signing, 'time', lambda: 1000)

    kwargs.setdefault('secret_key', base64.b32decode('DEADBEEF'))
    actual = signing.sign_url_path(url, **kwargs)
    assert actual == expected


@pytest.mark.parametrize('url_path, query_args, kwargs', (
    ("/foo/bar", {"_": "YJEYWGBKGUVZS", "signature": "QKUNPLEDOMFVU2NBTEASPR2J4B524KFMG4GMW2NJISVG2RQQVJEA"}, {}),
    ("/foo/bar", {"a": "1", "b": "2", "_": "YJEYWGBKGUVZS", "signature": "TU773VE25K5UFPHV6DGD5NXT7D74SFZYKVMEB6ZRONK2UXHT72EQ"}, {}),
    ("/foo/bar", {"a": "1", "b": "2", "expires": "1020", "_": "YJEYWGBKGUVZS", "signature": "XRKDRGPSUXFQUG36CNSOFY6RSWJFYSKTUOORJIQUUDG4WBCZOKUA"}, {}),
))
def test_verify_url_path(monkeypatch, url_path, query_args, kwargs):
    # Monkey patch to fix token and time values.
    monkeypatch.setattr(signing, 'token', lambda: 'YJEYWGBKGUVZS')
    monkeypatch.setattr(signing, 'time', lambda: 1010)

    kwargs.setdefault('secret_key', base64.b32decode('DEADBEEF'))
    assert signing.verify_url_path(url_path, query_args, **kwargs)
