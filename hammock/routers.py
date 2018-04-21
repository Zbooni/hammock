"""Custom routers."""

import rest_framework
import semver

from rest_framework import routers
from rest_framework.settings import api_settings


class NonDefaultPermissionApiRootRouter(routers.DefaultRouter):
    """Router with a permission different from the default for the root."""

    def __init__(self, *args, **kwargs):
        """Initialize router."""
        root_view_permission_classes = kwargs.pop(
            'root_view_permission_classes', None)

        super(
            NonDefaultPermissionApiRootRouter, self).__init__(*args, **kwargs)

        self.root_view_permission_classes = (
            root_view_permission_classes or
            api_settings.DEFAULT_PERMISSION_CLASSES)

    def get_api_root_view(self, api_urls=None):
        """Return the view for the API root."""
        args = []
        if semver.parse_version_info(rest_framework.VERSION) >= (3, 4, 0):
            args = [api_urls]
        api_root_view = super(
            NonDefaultPermissionApiRootRouter, self
        ).get_api_root_view(*args)

        BaseApiRoot = api_root_view.cls

        class ApiRoot(BaseApiRoot):
            # the permission for the root view; set to allow anyone access
            permission_classes = self.root_view_permission_classes

        return ApiRoot.as_view()
