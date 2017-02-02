"""Custom routers."""

from rest_framework import routers
from rest_framework.settings import api_settings


class NonDefaultPermissionApiRootRouter(routers.DefaultRouter):
    """Router with a permission different from the default for the root."""

    def __init__(self, trailing_slash=True, root_view_permission_classes=None):
        """Initialize router."""
        super(NonDefaultPermissionApiRootRouter, self).__init__(
            trailing_slash=trailing_slash)

        self.root_view_permission_classes = (
            root_view_permission_classes or
            api_settings.DEFAULT_PERMISSION_CLASSES)

    def get_api_root_view(self, api_urls=None):
        """Return the view for the API root."""
        api_root_view = super(
            NonDefaultPermissionApiRootRouter, self
        ).get_api_root_view(
            api_urls=api_urls)
        BaseApiRoot = api_root_view.cls

        class ApiRoot(BaseApiRoot):
            # the permission for the root view; set to allow anyone access
            permission_classes = self.root_view_permission_classes

        return ApiRoot.as_view()
