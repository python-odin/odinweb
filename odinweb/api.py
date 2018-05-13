"""
Odin Web
~~~~~~~~

Web APIs utilising Odin for encoding/decoding and validation.

"""
__authors__ = "Tim Savage"
__author_email__ = "tim@savage.company"
__copyright__ = "Copyright (C) 2016-2017 Tim Savage"

from .constants import (
    HTTPStatus,
    Method,
    PathType,
    In,
    Type,
)  # noqa
from .containers import (
    ResourceApi,
    ApiCollection,
    ApiVersion,
)  # noqa
from .decorators import (
    Operation, ListOperation, ResourceOperation, security,
    # Basic routes
    collection, collection_action, action, operation,
    # Shortcuts
    listing, create, detail, update, patch, delete,
)  # noqa
from .exceptions import (
    ImmediateHttpResponse,
    HttpError,
    PermissionDenied,
    AccessDenied,
)  # noqa
from .helpers import (
    get_resource,
    create_response,
)  # noqa
from .data_structures import (
    UrlPath,
    PathParam,
)  # noqa
