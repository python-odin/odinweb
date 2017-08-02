import pytest

from odinweb import api
from odinweb import doc
from odinweb.constants import HTTPStatus
from odinweb.data_structures import Param, Response, DefaultResponse


def test_deprecated():
    @doc.deprecated
    @api.Operation
    def a():
        pass

    assert a.deprecated

    @api.Operation
    @doc.deprecated
    def b():
        pass

    assert b.deprecated


def test_add_param():
    @doc.add_param(Param.query('foo'))
    @api.Operation
    def a():
        pass

    assert len(a.parameters) == 1
    assert Param.query('foo') in a.parameters

    @api.Operation
    @doc.add_param(Param.query('foo'))
    def b():
        pass

    assert len(b.parameters) == 1
    assert Param.query('foo') in b.parameters

    @doc.add_param(Param.query('foo'))
    @api.Operation
    @doc.add_param(Param.form('bar'))
    def c():
        pass

    assert len(c.parameters) == 2
    assert Param.query('foo') in c.parameters
    assert Param.form('bar') in c.parameters


def test_response():
    @doc.response(HTTPStatus.BAD_GATEWAY, "foo")
    @api.Operation
    def a():
        pass

    assert len(a.responses) == 2
    assert DefaultResponse('eek') in a.responses
    assert Response(HTTPStatus.BAD_GATEWAY, 'eek') in a.responses

    @api.Operation
    @doc.response(HTTPStatus.ACCEPTED, "foo")
    def b():
        pass

    assert len(b.responses) == 2
    assert DefaultResponse('eek') in b.responses
    assert Response(HTTPStatus.ACCEPTED, 'eek') in b.responses

    @doc.response(HTTPStatus.CONTINUE, "foo")
    @api.Operation
    @doc.response(HTTPStatus.FORBIDDEN, "bar")
    def c():
        pass

    assert len(c.responses) == 3
    assert DefaultResponse('eek') in c.responses
    assert Response(HTTPStatus.CONTINUE, 'eek') in c.responses
    assert Response(HTTPStatus.FORBIDDEN, 'eek') in c.responses


def test_produces():
    @doc.produces('text/plain', 'text/html')
    @api.Operation
    def a():
        pass

    assert len(a.produces) == 2
    assert {'text/plain', 'text/html'} == a.produces

    @api.Operation
    @doc.produces('text/plain', 'text/html')
    def b():
        pass

    assert len(b.produces) == 2
    assert {'text/plain', 'text/html'} == b.produces

    @doc.produces('text/plain', 'text/html')
    @api.Operation
    @doc.produces('text/xml')
    def c():
        pass

    assert len(c.produces) == 3
    assert {'text/plain', 'text/html', 'text/xml'} == c.produces


@pytest.mark.parametrize('values', (
    (1,),
    ('text/plain', 2),
    ('text/plain', 2, 'text/html'),
))
def test_produces__bad_values(values):
    with pytest.raises(ValueError):
        @doc.produces(*values)
        def x():
            pass
