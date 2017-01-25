"""Custom APIView base classes."""

from rest_framework import views


class NonModelAPIView(views.APIView):
    """
    Base APIView for non-model resources.

    Implementation mostly copied/based from `GenericAPIView`, which is
    for model-based resources.

    """

    pagination_class = None

    def get_serializer_class(self):
        """Return the serializer class."""
        assert self.serializer_class is not None, (
            "'%s' should either include a `serializer_class` attribute, "
            "or override the `get_serializer_class()` method."
            % self.__class__.__name__
        )

        return self.serializer_class

    def get_serializer_context(self):
        """Return extra context to provide to the serializer."""
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }

    def get_serializer(self, *args, **kwargs):
        """Return the serializer instance."""
        serializer_class = self.get_serializer_class()
        kwargs['context'] = self.get_serializer_context()
        return serializer_class(*args, **kwargs)

    @property
    def paginator(self):
        """The paginator instance associated with the view, or `None`."""
        if not hasattr(self, '_paginator'):
            if self.pagination_class is None:
                self._paginator = None
            else:
                self._paginator = self.pagination_class()
        return self._paginator

    def paginate_data(self, data):
        """Return the paginated `data`."""
        if self.paginator is None:
            return None
        return self.paginator.paginate_data(
            data, self.request, view=self)

    def get_paginated_response(self, data):
        """Return a paginated `Response` object for the given output data."""
        assert self.paginator is not None
        return self.paginator.get_paginated_response(data)
