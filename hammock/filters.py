"""Custom filters."""

from django.core.exceptions import ImproperlyConfigured
from rest_framework import filters


class AuthenticatedUserAccessFilter(filters.BaseFilterBackend):
    """Filter that returns objects accessible to the authenticated user."""

    def filter_queryset(self, request, queryset, view):
        """Return queryset filtered by the authenticated user."""
        if not view.user_id_filter_kwarg:
            raise ImproperlyConfigured(
                "`user_id_filter_kwarg` is not set in the view. Please "
                "set it to the filter kwarg to use to filter the "
                "object with the authenticated user's ID.".format(
                    self.__class__.__name__))

        # Whether or not staff user accounts gets filtered querysets as
        # well. Set to `False` in the view to give staff accounts
        # unfiltered querysets
        filter_staff_accounts = getattr(view, 'filter_staff_accounts', True)

        if not filter_staff_accounts and request.user.is_staff:
            # authenticated user is admin, return full queryset
            return queryset

        # authenticated user is regular user, filter queryset by its ID
        filter_kwargs = {
            view.user_id_filter_kwarg: request.user.id,
        }
        return queryset.filter(**filter_kwargs)
