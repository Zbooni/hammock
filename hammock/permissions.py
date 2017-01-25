"""Custom permission classes for `rest_framework`."""

from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """Admins get full access, non-admins read-only."""

    def has_permission(self, request, view):
        """Return `True` if read-only method or is an admin (staff) user."""
        return (
            request.method in ('GET', 'HEAD', 'OPTIONS') or
            request.user and request.user.is_staff
        )
