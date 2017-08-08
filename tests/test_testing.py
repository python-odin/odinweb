from odinweb import testing


def test_mock_request():
    target = testing.MockRequest()
    testing.check_request_proxy(target)
