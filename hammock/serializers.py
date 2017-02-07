"""Custom serializers for `rest_framework`."""

from django.core.exceptions import ImproperlyConfigured
from django.db import models

from rest_framework import fields
from rest_framework import serializers


class PolymorphicModelListSerializer(serializers.ListSerializer):
    """ListSerializer that switches child serializers based on the instance."""

    def to_representation(self, data):
        """Return list of primitive datatypes representation of members."""
        iterable = data.all() if isinstance(data, models.Manager) else data

        # the child is now the parent in this context
        # (and `self` -- this `ListSerializer` -- essentially the grandparent)
        parent = self.child

        # the `Meta` class of the singular serializer
        parent_meta = parent.Meta

        serialized_data = []
        for item in iterable:
            assert isinstance(item, parent_meta.model)

            # get the serializer class for the current instance
            differentiator = getattr(item, parent_meta.differentiator_field)
            child_serializer_class = (
                parent_meta.child_serializer_map[differentiator])

            # get the model class and instance
            child_model = child_serializer_class.Meta.model
            parent_model = parent_meta.model

            parent_attr_name = next(
                f.attname for f in child_model._meta.fields
                if f.related_model == parent_model)

            child_model_inst = child_model.objects.get(
                **{
                    parent_meta.differentiator_field: getattr(
                        item, parent_meta.differentiator_field),
                    parent_attr_name: item.id
                })

            # serialize the item using its serializer and append to list
            child_serializer = child_serializer_class(
                child_model_inst, context=self._context)
            serialized_data.append(
                child_serializer.to_representation(child_model_inst))

        return serialized_data


class PolymorphicModelSerializer(serializers.ModelSerializer):
    """Serializer class that changes instance based on data."""

    def __new__(cls, instance=None, data=fields.empty, *args, **kwargs):
        """Return serializer instance."""
        try:
            meta = cls.Meta
        except AttributeError:
            raise ImproperlyConfigured(
                '`{}` class needs to have a `Meta` class with '
                '`differentiator_field` and `child_serializer_map` '
                'attributes defined.'.format(cls.__name__))

        if not getattr(meta, 'differentiator_field', None):
            raise ImproperlyConfigured(
                '`differentiator_field` attribute should be defined in '
                '`{}.Meta` class.'.format(cls.__name__))

        if not getattr(meta, 'child_serializer_map', None):
            raise ImproperlyConfigured(
                '`child_serializer_map` attribute should be defined in '
                '`{}.Meta` class.'.format(cls.__name__))

        # inject `PolymorphicModelListSerializer` as `list_serializer_class`
        # if nothing defined
        if not getattr(meta, 'list_serializer_class', None):
            meta.list_serializer_class = PolymorphicModelListSerializer

        if kwargs.pop('many', False):
            return cls.many_init(instance, data, *args, **kwargs)

        #
        # Serializer switch
        #

        differentiator_value = cls._get_differentiator_value(instance, data)
        if differentiator_value:
            # get class based on differentiator value
            serializer_class = (
                cls.Meta.child_serializer_map[differentiator_value]
            )

            if instance:
                # switch instance to the extended model

                # get the model class and instance
                model = serializer_class.Meta.model
                parent_model = cls.Meta.model

                parent_attr_name = next(
                    f.attname for f in model._meta.fields
                    if f.related_model == parent_model)

                instance = model.objects.get(
                    **{
                        cls.Meta.differentiator_field: differentiator_value,
                        parent_attr_name: instance.id
                    })

            # instantiate and return serializer
            return serializer_class(instance, data, *args, **kwargs)

        return super(PolymorphicModelSerializer, cls).__new__(
            cls, instance, data, *args, **kwargs)

    @classmethod
    def _get_differentiator_value(cls, instance=None, data=fields.empty):
        """Return the value of the differentiator from `data` or `instance`."""
        differentiator_value = None

        if data is not fields.empty:
            differentiator_value = data.get(
                getattr(cls.Meta, 'differentiator_field'))

        if not differentiator_value and instance:
            try:
                differentiator_value = getattr(
                    instance, getattr(cls.Meta, 'differentiator_field'))
            except AttributeError:
                pass

        return differentiator_value
