"""Custom pagination classes."""

from rest_framework import pagination


class NonModelPaginationBase(object):
    """Base pagination class for non-model resources."""

    display_page_controls = False

    def paginate_data(self, data, request, view=None):
        """Return the paginated data."""
        raise NotImplementedError(
            'Subclass `{}` should implement `paginate_data` method.')

    def get_paginated_response(self, data):
        """Return response with paginated data."""
        raise NotImplementedError(
            'Subclass `{}` should implement `get_paginated_response` method.')


class NonModelLimitOffsetPagination(
        pagination.LimitOffsetPagination, NonModelPaginationBase):
    """Paginator for non-model resources, with limit, offset parameters."""

    def paginate_data(self, data, request, view=None):
        """Return the paginated data."""
        # just call `LimitOffsetPagination.paginate_queryset` method as
        # its implementation is compatible with non-model data sources.
        return self.paginate_queryset(data, request, view)
