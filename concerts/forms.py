from django import forms


class ConcertTicketOrderForm(forms.Form):
    """Form for ordering concert tickets (guest checkout)."""
    name = forms.CharField(max_length=200, label="Full Name")
    email = forms.EmailField()
    phone = forms.CharField(max_length=30, required=False)

    ticket_type = forms.ChoiceField(
        choices=[('full', 'Full Price'), ('discount', 'Discount')],
        widget=forms.RadioSelect
    )
    quantity = forms.IntegerField(min_value=1, max_value=10, initial=1)

    def __init__(self, *args, concert=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.concert = concert

        # Update ticket type choices with prices
        if concert:
            choices = [('full', f'Full Price - £{concert.full_price}')]
            if concert.discount_price:
                choices.append(('discount', f'{concert.discount_label} - £{concert.discount_price}'))
            self.fields['ticket_type'].choices = choices

            # Limit quantity to available tickets
            if concert.tickets_remaining is not None:
                self.fields['quantity'].max_value = min(10, concert.tickets_remaining)

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if self.concert and self.concert.tickets_remaining is not None:
            if quantity > self.concert.tickets_remaining:
                raise forms.ValidationError(
                    f'Only {self.concert.tickets_remaining} tickets remaining.'
                )
        return quantity

    def get_unit_price(self):
        """Get the unit price based on ticket type."""
        ticket_type = self.cleaned_data.get('ticket_type')
        if ticket_type == 'discount':
            return self.concert.discount_price
        return self.concert.full_price

    def get_total_price(self):
        """Calculate total price."""
        return self.get_unit_price() * self.cleaned_data.get('quantity', 1)
