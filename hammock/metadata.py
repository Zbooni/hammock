"""Metadata classes."""

from collections import OrderedDict

from django.utils.encoding import force_text

from rest_framework import metadata
from rest_framework import serializers


class SimplerMetadata(metadata.SimpleMetadata):
    """
    Metadata implementation simpler than `SimpleMetadata`.

    This metadata class overrides DRF's `SimpleMetadata.get_field_info`
    implementation so it can instead do an `insinstance` check for a
    `ChoiceField` rather than a `hasattr` for a `choices` attribute on
    a `Field` instance.  This results in a faster execution as it no
    longer needs to introspect each instance for the presence of the
    attribute and instead checks the class info of the object.  Of
    course this could result in an incorrect metadata if the serializer
    has overridden the field and used something else for a field with
    `choices` (DRF, by default, changes the field to `ChoiceField` if
    the model has a `choices` attribute) but, at the moment, it is not
    causing an issue for us.  If this causes an issue in the future then
    we might need to look into using some other way to get an endpoint's
    metadata (i.e. not via an `OPTIONS` request, see
    https://www.mnot.net/blog/2012/10/29/NO_OPTIONS).

    """

    def get_field_info(self, field, only_if=None):
        """Return metadata dictionary of a serializer field."""
        field_info = OrderedDict()
        field_info['type'] = self.label_lookup[field]
        field_info['required'] = getattr(field, 'required', False)

        attrs = [
            'read_only', 'label', 'help_text',
            'min_length', 'max_length',
            'min_value', 'max_value'
        ]

        for attr in attrs:
            value = getattr(field, attr, None)
            if value is not None and value != '':
                field_info[attr] = force_text(value, strings_only=True)

        if getattr(field, 'child', None):
            field_info['child'] = self.get_field_info(field.child)
        elif getattr(field, 'fields', None):
            field_info['children'] = self.get_serializer_info(field)

        if (not field_info.get('read_only')
                and isinstance(field, serializers.ChoiceField)):
            field_info['choices'] = [
                {
                    'value': choice_value,
                    'display_name': force_text(choice_name, strings_only=True)
                }
                for choice_value, choice_name in field.choices.items()
            ]

        return field_info
