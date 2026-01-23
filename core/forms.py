"""
Form utilities and mixins for consistent styling.
"""
from django import forms


# Standard Tailwind CSS classes for form widgets
FORM_INPUT_CLASS = 'w-full px-3 py-2 border border-primary-300 rounded-lg focus:ring-2 focus:ring-accent-500 focus:border-accent-500'
FORM_SELECT_CLASS = FORM_INPUT_CLASS
FORM_TEXTAREA_CLASS = FORM_INPUT_CLASS


class StyledFormMixin:
    """
    Mixin that applies consistent Tailwind CSS styling to all form fields.

    Usage:
        class MyForm(StyledFormMixin, forms.ModelForm):
            class Meta:
                model = MyModel
                fields = ['field1', 'field2']
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_styling()

    def _apply_styling(self):
        """Apply Tailwind classes to all form fields, preserving existing attributes."""
        for field_name, field in self.fields.items():
            # Skip if class is already set
            if field.widget.attrs.get('class'):
                continue

            # Apply appropriate class based on widget type
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs['class'] = FORM_TEXTAREA_CLASS
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = FORM_SELECT_CLASS
            elif isinstance(field.widget, (forms.TextInput, forms.EmailInput,
                                           forms.NumberInput, forms.URLInput,
                                           forms.PasswordInput, forms.DateInput,
                                           forms.TimeInput, forms.DateTimeInput)):
                field.widget.attrs['class'] = FORM_INPUT_CLASS
            elif isinstance(field.widget, forms.CheckboxInput):
                # Don't apply full styling to checkboxes
                pass
