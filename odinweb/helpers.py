# Type imports
from typing import Iterable, Callable, Any, Optional

from odin.exceptions import CodecDecodeError

from .constants import HTTPStatus
from .data_structures import HttpResponse
from .exceptions import HttpError

__all__ = ('get_resource', 'create_response')


def parse_content_type(value):
    # type: (str) -> str
    """
    Parse out the content type from a content type header.

    >>> parse_content_type('application/json; charset=utf8')
    'application/json'

    """
    if not value:
        return ''

    return value.split(';')[0].strip()


def resolve_content_type(type_resolvers, request):
    # type: (Iterable[Callable((Any,), str), Any]) -> Optional[str]
    """
    Resolve content types from a request.
    """
    for resolver in type_resolvers:
        content_type = parse_content_type(resolver(request))
        if content_type:
            return content_type


def get_resource(request, resource, allow_multiple=False):
    """
    Get a resource instance from ``request.body``.
    """
    # Decode the request body.
    body = request.body
    if isinstance(body, bytes):
        try:
            body = body.decode('UTF8')
        except UnicodeDecodeError as ude:
            raise HttpError(HTTPStatus.BAD_REQUEST, 40099, "Unable to decode request body.", str(ude))

    try:
        instance = request.request_codec.loads(body, resource=resource, full_clean=True)

    except ValueError as ve:
        raise HttpError(HTTPStatus.BAD_REQUEST, 40098, "Unable to load resource.", str(ve))

    except CodecDecodeError as cde:
        raise HttpError(HTTPStatus.BAD_REQUEST, 40096, "Unable to decode body.", str(cde))

    # Check an array of data hasn't been supplied
    if not allow_multiple and isinstance(instance, list):
        raise HttpError(HTTPStatus.BAD_REQUEST, 40097, "Expected a single resource not a list.")

    return instance


def create_response(request, body=None, status=None, headers=None):
    """
    Generate a HttpResponse.

    :param request: Request object
    :param body: Body of the response
    :param status: HTTP status code
    :param headers: Any headers.

    """
    if body is None:
        return HttpResponse(None, status or HTTPStatus.NO_CONTENT, headers)
    else:
        body = request.response_codec.dumps(body)
        response = HttpResponse(body, status or HTTPStatus.OK, headers)
        response.set_content_type(request.response_codec.CONTENT_TYPE)
        return response
