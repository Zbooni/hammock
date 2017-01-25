"""Custom filters."""

import warnings

from django.core.exceptions import ImproperlyConfigured
from rest_framework import filters


class AuthenticatedUserAccessFilter(filters.BaseFilterBackend):
    """Filter that returns objects accessible to the authenticated user."""

    def filter_queryset(self, request, queryset, view):
        """Return queryset filtered by the authenticated user."""
        view_user_pk_attributes = (
            getattr(view, 'user_pk_filter_kwarg', None),
            getattr(view, 'user_id_filter_kwarg', None),
        )
        if not any(view_user_pk_attributes):
            raise ImproperlyConfigured(
                "`user_pk_filter_kwarg` is not set in the view. Please "
                "set it to the filter kwarg to use to filter the "
                "object with the authenticated user's primary key.".format(
                    self.__class__.__name__))

        if all(view_user_pk_attributes):
            warnings.warn(
                'Both `user_id_filter_kwarg` and `user_pk_filter_kwarg` '
                'are set in the view. `user_pk_filter_kwarg` will be '
                'used.')

        user_pk_filter_kwarg = (
            getattr(view, 'user_pk_filter_kwarg', None) or
            getattr(view, 'user_id_filter_kwarg', None))

        user_pk_field = getattr(view, 'user_pk_field', 'id')

        # Whether or not staff user accounts gets filtered querysets as
        # well. Set to `False` in the view to give staff accounts
        # unfiltered querysets
        filter_staff_accounts = getattr(view, 'filter_staff_accounts', True)

        if not filter_staff_accounts and request.user.is_staff:
            # authenticated user is admin, return full queryset
            return queryset

        # authenticated user is regular user, filter queryset by its ID
        filter_kwargs = {
            user_pk_filter_kwarg: getattr(request.user, user_pk_field),
        }
        return queryset.filter(**filter_kwargs)
