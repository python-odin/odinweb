import pytest

from odinweb import signing

#
# # class TestSigning(object):
# #     @pytest.mark.parametrize('path,secret_key,query_args,expected'.split(','), (
# #         ('/foo/bar/', '123', {}, 'd9ee4f25134a77cfc587d00c256976380c702fded3111634d6bff376c867a7fd'),
# #         ('/foo/bar/', '123', {'foo': 'bar'}, '3996f22d0def3c4a2d4027e23bf3528cc514c088e3c93a87970daa5a80b63823'),
# #     ))
# #     def test_generate_signature(self, path, secret_key, query_args, expected):
# #         actual = signing._generate_signature(path, secret_key, query_args)
# #
# #         assert actual == expected
