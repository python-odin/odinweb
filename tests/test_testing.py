from odinweb import testing


def test_mock_request():
    target = testing.MockRequest()
    testing.test_request_proxy(target)
