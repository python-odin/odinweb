# -*- coding: utf-8 -*-
from odinweb.api import ResourceApi
from odinweb.exceptions import PermissionDenied


class LoginRequiredMixin(ResourceApi):
    """
    Ensure that a user has logged in.
    """
    def handle_authorisation(self, request):
        """
        Evaluate if a request is authorised.
        """
        if not request.user.is_authenticated():
            raise PermissionDenied('Login required')
