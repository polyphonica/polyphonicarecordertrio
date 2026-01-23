from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from core.image_utils import process_uploaded_image


class Concert(models.Model):
    """Concert/performance listing."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('cancelled', 'Cancelled'),
    ]

    TICKET_SOURCE_CHOICES = [
        ('internal', 'Sell on this site'),
        ('external', 'External ticket link'),
        ('door', 'Available on the door'),
        ('none', 'No tickets (free entry or private)'),
    ]

    # Basic info
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField()

    # Date and time
    date = models.DateField()
    time = models.TimeField()
    doors_open = models.TimeField(blank=True, null=True, help_text="When doors open (optional)")

    # Venue
    venue_name = models.CharField(max_length=200)
    venue_address = models.TextField(blank=True)
    venue_postcode = models.CharField(max_length=20, blank=True)
    venue_map_link = models.URLField(blank=True, help_text="Google Maps or similar link")

    # Image
    image = models.ImageField(upload_to='concerts/', blank=True, null=True)

    # Programme
    programme = models.ForeignKey(
        'repertoire.Programme',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='concerts',
        help_text="Link to the repertoire programme for this concert"
    )

    # Tickets
    ticket_source = models.CharField(max_length=20, choices=TICKET_SOURCE_CHOICES, default='external')
    external_ticket_url = models.URLField(blank=True, help_text="Link to external ticket seller")

    # Pricing (for internal sales)
    full_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    discount_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    discount_label = models.CharField(
        max_length=100,
        default="Concessions (seniors, students, disabled)",
        help_text="Description of who qualifies for discount"
    )

    # Capacity (for internal sales)
    capacity = models.PositiveIntegerField(null=True, blank=True, help_text="Leave blank for unlimited")
    tickets_sold = models.PositiveIntegerField(default=0)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date', 'time']

    def __str__(self):
        return f"{self.title} - {self.date}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Concert.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        # Resize image on upload for consistent quality
        process_uploaded_image(self, 'image', max_width=1200, max_height=800)

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('concerts:detail', kwargs={'slug': self.slug})

    @property
    def is_past(self):
        """Check if concert date has passed."""
        from django.utils import timezone
        return self.date < timezone.now().date()

    @property
    def is_sold_out(self):
        """Check if concert is sold out (only relevant for internal sales)."""
        if self.ticket_source != 'internal' or not self.capacity:
            return False
        return self.tickets_sold >= self.capacity

    @property
    def tickets_remaining(self):
        """Get remaining tickets (only relevant for internal sales)."""
        if self.ticket_source != 'internal' or not self.capacity:
            return None
        return max(0, self.capacity - self.tickets_sold)


class ConcertTicketOrder(models.Model):
    """Guest ticket order for a concert."""
    TICKET_TYPE_CHOICES = [
        ('full', 'Full Price'),
        ('discount', 'Discount'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]

    concert = models.ForeignKey(Concert, on_delete=models.CASCADE, related_name='orders')

    # Guest details (no account required)
    email = models.EmailField()
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=30, blank=True)

    # Tickets
    ticket_type = models.CharField(max_length=20, choices=TICKET_TYPE_CHOICES)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    total_price = models.DecimalField(max_digits=8, decimal_places=2)

    # Payment
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    stripe_checkout_session_id = models.CharField(max_length=255, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    # Confirmation
    confirmation_sent = models.BooleanField(default=False)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.concert.title} ({self.quantity} tickets)"
