# -*- coding: utf-8 -*-
"""
Resources
~~~~~~~~~

Common resources for use in APIs.

"""
import odin

from odin.fields import Field


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
    
    status = odin.IntegerField(
        help_text="HTTP status code of the response."
    )
    code = odin.IntegerField(
        help_text="Custom application specific error code that references into"
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
