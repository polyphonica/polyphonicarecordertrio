from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class StripeTransaction(models.Model):
    """
    Stores Stripe fee information for payments.
    Links to either a workshop registration or concert ticket order.
    """
    TRANSACTION_TYPE_CHOICES = [
        ('workshop', 'Workshop Registration'),
        ('concert', 'Concert Ticket'),
    ]

    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)

    # Link to source (only one will be populated)
    workshop_registration = models.OneToOneField(
        'workshops.WorkshopRegistration',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='stripe_transaction'
    )
    concert_order = models.OneToOneField(
        'concerts.ConcertTicketOrder',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='stripe_transaction'
    )

    # Stripe identifiers
    payment_intent_id = models.CharField(max_length=255, db_index=True)
    charge_id = models.CharField(max_length=255, blank=True)
    balance_transaction_id = models.CharField(max_length=255, blank=True)

    # Financial amounts (stored in pence for precision)
    gross_amount = models.PositiveIntegerField(help_text="Amount in pence")
    stripe_fee = models.PositiveIntegerField(help_text="Stripe fee in pence")
    net_amount = models.PositiveIntegerField(help_text="Net amount in pence")

    # Timestamp from Stripe
    transaction_date = models.DateTimeField(db_index=True)

    # Metadata
    synced_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-transaction_date']
        indexes = [
            models.Index(fields=['transaction_type', 'transaction_date']),
        ]

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.payment_intent_id[:20]}..."

    @property
    def gross_pounds(self):
        """Gross amount in pounds."""
        return self.gross_amount / 100

    @property
    def fee_pounds(self):
        """Stripe fee in pounds."""
        return self.stripe_fee / 100

    @property
    def net_pounds(self):
        """Net amount in pounds."""
        return self.net_amount / 100

    def get_related_object(self):
        """Return the linked workshop registration or concert order."""
        return self.workshop_registration or self.concert_order


class ExpenseCategory(models.TextChoices):
    VENUE_HIRE = 'venue_hire', 'Venue Hire'
    REFRESHMENTS = 'refreshments', 'Refreshments'
    OTHER = 'other', 'Other'


class Expense(models.Model):
    """
    Tracks expenses that can be linked to workshops, concerts, or general.
    """
    # Category
    category = models.CharField(
        max_length=20,
        choices=ExpenseCategory.choices,
        default=ExpenseCategory.OTHER,
        db_index=True
    )

    # Description
    description = models.CharField(max_length=200)
    notes = models.TextField(blank=True)

    # Amount
    amount = models.DecimalField(max_digits=8, decimal_places=2)

    # Date of expense
    expense_date = models.DateField(db_index=True)

    # Optional links to events (null = general expense)
    workshop = models.ForeignKey(
        'workshops.Workshop',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses'
    )
    concert = models.ForeignKey(
        'concerts.Concert',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses'
    )

    # Receipt
    receipt = models.FileField(
        upload_to='expense_receipts/%Y/%m/',
        blank=True,
        null=True,
        help_text="Upload receipt image or PDF"
    )

    # Audit trail
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='expenses_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-expense_date', '-created_at']
        indexes = [
            models.Index(fields=['category', 'expense_date']),
        ]

    def __str__(self):
        linked = ""
        if self.workshop:
            linked = f" (Workshop: {self.workshop.title})"
        elif self.concert:
            linked = f" (Concert: {self.concert.title})"
        return f"{self.description} - £{self.amount}{linked}"

    def clean(self):
        """Ensure only one of workshop/concert is linked."""
        if self.workshop and self.concert:
            raise ValidationError(
                "An expense can only be linked to either a workshop or a concert, not both."
            )

    @property
    def event(self):
        """Return linked event or None."""
        return self.workshop or self.concert

    @property
    def event_type(self):
        """Return type of linked event."""
        if self.workshop:
            return 'workshop'
        elif self.concert:
            return 'concert'
        return None
