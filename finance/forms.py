from django import forms
from .models import Expense
from workshops.models import Workshop
from concerts.models import Concert


class DateRangeForm(forms.Form):
    """Form for date range filtering."""
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_date')
        end = cleaned_data.get('end_date')

        if start and end and start > end:
            raise forms.ValidationError("Start date must be before end date.")

        return cleaned_data


class ExpenseForm(forms.ModelForm):
    """Form for creating/editing expenses."""

    class Meta:
        model = Expense
        fields = [
            'category', 'description', 'notes',
            'amount', 'expense_date',
            'workshop', 'concert', 'receipt'
        ]
        widgets = {
            'expense_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Order workshops and concerts by date (most recent first)
        self.fields['workshop'].queryset = Workshop.objects.order_by('-date')
        self.fields['concert'].queryset = Concert.objects.order_by('-date')

        # Make workshop/concert optional and add empty labels
        self.fields['workshop'].required = False
        self.fields['concert'].required = False
        self.fields['workshop'].empty_label = "-- No workshop --"
        self.fields['concert'].empty_label = "-- No concert --"

        # Notes and receipt are optional
        self.fields['notes'].required = False
        self.fields['receipt'].required = False

    def clean(self):
        cleaned_data = super().clean()
        workshop = cleaned_data.get('workshop')
        concert = cleaned_data.get('concert')

        if workshop and concert:
            raise forms.ValidationError(
                "An expense can only be linked to either a workshop or a concert, not both."
            )

        return cleaned_data
