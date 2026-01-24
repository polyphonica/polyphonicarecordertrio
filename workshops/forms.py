from django import forms
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from .models import WorkshopRegistration


class WorkshopRegistrationForm(forms.Form):
    """
    Workshop registration form that handles both logged-in users
    and new users (auto-creating accounts).
    """
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField()
    phone = forms.CharField(max_length=30, required=False)

    # In-person workshop fields
    emergency_contact = forms.CharField(
        max_length=200,
        required=False,
        help_text="Name and phone number of emergency contact"
    )
    instruments = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}),
        required=False,
        help_text="What instruments will you be bringing?"
    )

    special_requirements = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text="Dietary, accessibility, or other requirements"
    )
    terms_accepted = forms.BooleanField(
        required=True,
        label="I accept the terms and conditions"
    )

    def __init__(self, *args, user=None, workshop=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.workshop = workshop

        # Pre-fill if user is logged in
        if user and user.is_authenticated:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
            # Make email read-only for logged-in users
            self.fields['email'].widget.attrs['readonly'] = True

        # Make in-person fields required for in-person/hybrid workshops
        if workshop and workshop.is_in_person:
            self.fields['emergency_contact'].required = True
            self.fields['instruments'].required = True
        else:
            # Hide these fields for online-only workshops
            del self.fields['emergency_contact']
            del self.fields['instruments']
            del self.fields['special_requirements']

    def clean_email(self):
        email = self.cleaned_data['email']

        # If user is logged in, keep their email
        if self.user and self.user.is_authenticated:
            return self.user.email

        # Check if email already has an account
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists. "
                "Please log in first, or use a different email."
            )

        return email

    def get_or_create_user(self):
        """
        Returns the user for this registration.
        Creates a new account if the user isn't logged in.
        Returns (user, created, password) tuple.
        """
        if self.user and self.user.is_authenticated:
            # Update name if changed
            if (self.user.first_name != self.cleaned_data['first_name'] or
                self.user.last_name != self.cleaned_data['last_name']):
                self.user.first_name = self.cleaned_data['first_name']
                self.user.last_name = self.cleaned_data['last_name']
                self.user.save()
            return self.user, False, None

        # Create new user
        email = self.cleaned_data['email']
        first_name = self.cleaned_data['first_name']
        last_name = self.cleaned_data['last_name']

        # Generate username from email (before @)
        base_username = email.split('@')[0].lower()
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        # Generate random password
        password = get_random_string(12)

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        return user, True, password
