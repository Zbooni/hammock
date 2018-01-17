"""Custom APIView base classes."""

from django.db import transaction
from django.utils.decorators import method_decorator

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


class AtomicNonIdempotentActionViewSetMixin(object):
    """
    Wraps non-idempotent viewset action methods in a database transaction.

    Decorates `create`, `update`, and `destroy` methods with the
    `transaction.atomic` decorator.  Since this mixin class decorates
    methods, this needs to appear first in the class' derived classes
    list.  SQL operations from derived classes that appears before this
    mixin in the list will operate outside of the database transaction
    and will not be rolled back in case of exceptions.

    """

    @method_decorator(transaction.atomic)
    def create(self, request, *args, **kwargs):
        """
        Create resource.

        This method wraps the superclass' `create` method in a
        `transaction.atomic` context so errors that occur within the
        method will cause all pending operations to rollback.

        """
        return super(AtomicNonIdempotentActionViewSetMixin, self).create(
            request, *args, **kwargs)

    @method_decorator(transaction.atomic)
    def update(self, request, *args, **kwargs):
        """
        Update the resource.

        This method wraps the superclass' `update` method in a
        `transaction.atomic` context so errors that occur within the
        method will cause all pending operations to rollback.

        """
        return super(AtomicNonIdempotentActionViewSetMixin, self).update(
            request, *args, **kwargs)

    @method_decorator(transaction.atomic)
    def destroy(self, request, *args, **kwargs):
        """
        Destroy (delete) the resource.

        This method wraps the superclass' `destroy` method in a
        `transaction.atomic` context so errors that occur within the
        method will cause all pending operations to rollback.

        """
        return super(AtomicNonIdempotentActionViewSetMixin, self).destroy(
            request, *args, **kwargs)
