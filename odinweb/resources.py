# -*- coding: utf-8 -*-
"""
Resources
~~~~~~~~~

Common resources for use in APIs.

"""
import odin

from typing import AnyStr  # noqa
from odin.fields import Field

from .constants import HTTPStatus  # noqa


class AnyField(Field):
    """
    Any value.
    """
    def to_python(self, value):
        return value


class Listing(odin.Resource):
    """
    Response for listing results. THis includes offset and count support for
    paging etc.

    """
    class Meta:
        namespace = None

    results = odin.ArrayField(
        help_text="List of resources."
    )
    limit = odin.IntegerField(
        null=True,
        help_text="Limit or page size of the result set"
    )
    offset = odin.IntegerField(
        default=0,
        help_text="Offset within the result set."
    )
    total_count = odin.IntegerField(
        null=True,
        help_text="The total number of items in the result set."
    )


class Error(odin.Resource):
    """
    Response returned for errors.

    The *meta* field should be utilised to provide additional information that
    is specific to the error, eg if validation field then meta would contain
    an object that maps field names to error messages.

    """
    class Meta:
        namespace = None

    @classmethod
    def from_status(cls, http_status, code_index=0, message=None, developer_message=None, meta=None):
        # type: (HTTPStatus, int, AnyStr, AnyStr, dict) -> Error
        """
        Automatically build an HTTP response from the HTTP Status code.
        
        :param http_status: 
        :param code_index: 
        :param message: 
        :param developer_message: 
        :param meta: 

        """
        return cls(http_status.value,
                   (http_status.value * 100) + code_index,
                   message or http_status.description,
                   developer_message or http_status.description,
                   meta)

    status = odin.IntegerField(
        help_text="HTTP status code of the response."
    )
    code = odin.IntegerField(
        help_text="Custom application specific error code that references into "
                  "the application."
    )
    message = odin.StringField(
        help_text="A message that can be displayed to an end user"
    )
    developer_message = odin.StringField(
        null=True,
        help_text="An error message suitable for the application developer"
    )
    meta = AnyField(
        null=True,
        help_text="Additional meta information that can help solve errors."
    )
