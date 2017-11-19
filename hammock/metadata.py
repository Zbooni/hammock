"""Metadata classes."""

from collections import defaultdict
from collections import OrderedDict

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.utils.encoding import force_text

from rest_framework import exceptions
from rest_framework import metadata
from rest_framework import serializers
from rest_framework.request import clone_request


# python 2 only
class OrderedDefaultDict(OrderedDict, defaultdict):
    """A defaultdict that keeps the ordering of its inserted keys."""

    def __init__(self, default_factory=None, *args, **kwargs):
        """Initialize the defaultdict and the OrderedDict."""
        super(OrderedDefaultDict, self).__init__(*args, **kwargs)
        self.default_factory = default_factory


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


class StateTransitioningFieldMetadataMixin(object):
    """Metadata class mixin for serializers with state transitioning field."""

    def get_field_info(self, field):
        """Return field info."""
        field_info = super(
            StateTransitioningFieldMetadataMixin, self).get_field_info(field)

        if (not field_info.get('read_only')
                and isinstance(field, serializers.ChoiceField)):
            # Field is a writable ChoiceField
            # Describe the choices

            field_info['choices'] = self.get_field_choices_info(
                field, field_name=field.field_name)

        return field_info

    def _get_valid_transition_previous_states(self, model, state):
        """Return valid previous states to be able to transition to `state`."""
        try:
            # return list of states `state` can transition from
            return next(
                t[1]
                for t in model.STATE_TRANSITIONS
                if state == t[0])
        except StopIteration:
            # `state` is not listed in `STATE_TRANSITIONS`, meaning
            # it is allowed to transition from any other state;
            # return all states except value of `state`

            # get states that can't be transitioned out of
            fixed_states = list(dict(model.STATE_TRANSITIONS).get(None, []))

            return [
                choice[0]
                for choice in next(
                    field
                    for field in model._meta.fields
                    if field.name == 'state'
                ).choices
                if choice[0] not in fixed_states + [state]
            ] + [None]

    def get_field_choices_info(self, field, field_name=None):
        """Return choices metadata dictionary for field."""
        choices = []
        for choice_value, choice_name in field.choices.items():
            choice = OrderedDict([
                ('value', choice_value),
                ('display_name', force_text(choice_name, strings_only=True)),
            ])

            # Set choice validity conditions for `state` field
            if (hasattr(field.parent.Meta.model, 'STATE_TRANSITIONS')
                    and field_name == 'state'):
                choice['valid'] = {
                    'only_if': {
                        'state': self._get_valid_transition_previous_states(
                            field.parent.Meta.model, choice_value),
                    }
                }

            choices.append(choice)

        return choices


class ObjectSpecificMetadata(SimplerMetadata):
    """Metadata class that generates metadata specific to a single object."""

    def determine_actions(self, request, view):
        """
        Return `dict` of actions for the viewset.

        For generic class based views we return information about
        the fields that are accepted for 'PUT' and 'POST' methods.

        If the request is for a specific object, generate metadata
        specific to that object by instantiating the serializer with
        the object and passing it to the `get_serializer_info` method.

        """
        actions = {}
        for method in {'PUT', 'POST'} & set(view.allowed_methods):
            view.request = clone_request(request, method)
            try:
                # Test global permissions
                if hasattr(view, 'check_permissions'):
                    view.check_permissions(view.request)
                # Test object permissions
                if method == 'PUT' and hasattr(view, 'get_object'):
                    view.get_object()
            except (exceptions.APIException, PermissionDenied, Http404):
                pass
            else:
                # If user has appropriate permissions for the view, include
                # appropriate metadata about the fields that should be
                # supplied.

                # If the URI we are getting the `OPTIONS` for is a URI for a
                # single object, pass the object as `instance` to the
                # serializer so the built metadata will be specific to that
                # object.
                if method == 'PUT' and hasattr(view, 'get_object'):
                    serializer = view.get_serializer(view.get_object())
                else:
                    serializer = view.get_serializer()

                actions[method] = self.get_serializer_info(serializer)
            finally:
                view.request = request

        return actions
