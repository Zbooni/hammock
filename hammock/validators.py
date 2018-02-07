"""Validator classes for serializers and serializer fields."""

from django.core.exceptions import ImproperlyConfigured
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _


class ValueTransitionValidator(object):
    """Validator for value transitions."""

    message = _(
        'Cannot transition from "{0}" to "{1}". '
        'Valid transitions for "{0}" are: [{2}].')

    def __init__(self, value_transitions, valid_values=None):
        """Initialize the validator with the transition rules."""
        self.value_transitions = value_transitions
        self.valid_values = valid_values

    def set_context(self, serializer_field):
        """Set runtime attributes needed to perform validation."""
        self.serializer_field = serializer_field
        self.field_name = serializer_field.source_attrs[0]
        self.serializer = serializer_field.parent
        self.instance = getattr(self.serializer, 'instance', None)

    def _get_valid_value_transitions(self, current_value):
        """Return list of values the `current_value` can transition to."""
        if current_value and current_value in dict(
                self.value_transitions).get(None, []):
            # disallow transitioning out of values without a valid
            # transition
            return []

        if (current_value not in dict(self.value_transitions)
                or current_value is None):
            # `current_value` is not listed in `value_transitions`,
            # meaning there are no restrictions to it--it is allowed to
            # transition to it from any other state; return all values
            # except `current_value`

            # get all valid values
            if not self.valid_values:
                if not getattr(self.serializer_field, 'choices', None):
                    raise ImproperlyConfigured(
                        '`valid_values` argument to '
                        '`ValueTransitionValidator` is required if '
                        "field is not a `ChoiceField`.")
                self.valid_values = self.serializer_field.choices.keys()

            # return all values except `current_value`, plus `None`
            return [
                choice
                for choice in self.valid_values
                if choice != current_value
            ] + [None]

        # return list of values `current_value` can transition to
        return [t[0] for t in self.value_transitions if current_value in t[1]]

    def __call__(self, value):
        """Run the validation."""
        current_value = getattr(self.instance, self.field_name)

        valid_value_transitions = self._get_valid_value_transitions(
            current_value)
        if value and value not in valid_value_transitions:
            raise ValidationError(
                self.message.format(
                    current_value, value,
                    ', '.join(
                        [
                            '"{}"'.format(s)
                            for s in valid_value_transitions
                        ])))
