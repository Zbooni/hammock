"""Custom APIView base classes."""

from django.core.exceptions import ImproperlyConfigured
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


class NestedModelViewSetMixin(object):
    """Mixin for `ModelViewSet` that is nested under another `ModelViewSet.`"""

    # The model class of the nesting `ModelViewSet`
    # e.g. `User` if the User model is the nesting model
    nesting_model = None

    # The field name of the nested model that references the parent model
    # e.g. `user` if the nested or related model's field to the `User`
    # model is `user`
    parent_field_name = None

    # The queryset filter keyword argument for matching the parent
    # model's primary key value
    # e.g. `user__pk`
    parent_lookup_field = None

    # The keyword argument in the URL configuration for the parent model
    parent_lookup_url_kwarg = None

    def get_nesting_model(self):
        """Return the parent model class."""
        if self.nesting_model is None:
            raise ImproperlyConfigured(
                '`nesting_model` is not set.  You either need to set '
                '`nesting_model` or implement `get_nesting_model` method.')

        return self.nesting_model

    def get_parent_field_name(self):
        """Return the field name referencing the related parent model."""
        if not self.parent_field_name:
            return self.get_nesting_model()._meta.model_name

        return self.parent_field_name

    def get_parent_lookup_field(self):
        """Return the queryset filter keyword argument for parent model pk."""
        if not self.parent_lookup_field:
            return '{}__pk'.format(self.get_nesting_model()._meta.model_name)

        return self.parent_lookup_field

    def get_parent_lookup_url_kwarg(self):
        """Return the keyword argument in the URL conf for the parent model."""
        if not self.parent_lookup_url_kwarg:
            return '{}_pk'.format(self.get_nesting_model()._meta.model_name)

        return self.parent_lookup_url_kwarg

    def get_nesting_model_instance(self):
        """Return the instance of the parent model."""
        return self.get_nesting_model().objects.get(
            pk=self.kwargs.get(self.get_parent_lookup_url_kwarg()))

    def get_queryset(self):
        """Return queryset to use in the viewset."""
        queryset = super(NestedModelViewSetMixin, self).get_queryset()

        if self.get_parent_lookup_url_kwarg() in self.kwargs:
            filter_kwargs = {
                self.get_parent_lookup_field(): self.kwargs.get(
                    self.get_parent_lookup_url_kwarg()),
            }
            queryset = queryset.filter(**filter_kwargs)

        return queryset

    def get_serializer(self, instance=None, *args, **kwargs):
        """
        Return the serializer with the instance with the nesting model object.

        Adds the nesting model instance in the serializer `instance` as it is
        needed when creating the model object, i.e. when the serializer's
        `instance` is `None`, which happens on create.

        """
        if instance is None:
            model_kwargs = {
                self.get_parent_field_name(): (
                    self.get_nesting_model_instance()),
            }
            instance = self.get_queryset().model(**model_kwargs)
        return (
            super(NestedModelViewSetMixin, self)
            .get_serializer(instance=instance, *args, **kwargs))
