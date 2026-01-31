from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify

from core.image_utils import process_uploaded_image


class Workshop(models.Model):
    """Workshop listing."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('cancelled', 'Cancelled'),
    ]

    DELIVERY_CHOICES = [
        ('online', 'Online'),
        ('in_person', 'In-Person'),
        ('hybrid', 'Hybrid'),
    ]

    # Basic info
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField()
    short_description = models.CharField(max_length=300, blank=True, help_text="Brief summary for listings")

    # Date and time
    date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()

    # Duration (for display)
    duration_hours = models.DecimalField(max_digits=4, decimal_places=1, default=2)

    # Delivery
    delivery_method = models.CharField(max_length=20, choices=DELIVERY_CHOICES, default='in_person')

    # Venue (for in-person)
    venue_name = models.CharField(max_length=200, blank=True)
    venue_address = models.TextField(blank=True)
    venue_postcode = models.CharField(max_length=20, blank=True)
    venue_map_link = models.URLField(blank=True)

    # Online details
    meeting_link = models.URLField(blank=True, help_text="Zoom/Meet link (only shown to registered participants)")
    meeting_password = models.CharField(max_length=50, blank=True)

    # Requirements
    prerequisites = models.TextField(blank=True, help_text="Required knowledge or skills")
    materials_needed = models.TextField(blank=True, help_text="What to bring")

    # Image
    image = models.ImageField(upload_to='workshops/', blank=True, null=True)

    # Pricing
    price = models.DecimalField(max_digits=8, decimal_places=2)

    # Capacity
    max_participants = models.PositiveIntegerField(default=20)
    current_registrations = models.PositiveIntegerField(default=0)
    legacy_bookings = models.PositiveIntegerField(
        default=0,
        help_text="Bookings from legacy system (e.g. Stripe) not yet imported"
    )
    hide_availability = models.BooleanField(
        default=False,
        help_text="Hide the availability section on the public page"
    )

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date', 'start_time']
        indexes = [
            models.Index(fields=['status', 'date'], name='workshop_status_date_idx'),
        ]

    def __str__(self):
        return f"{self.title} - {self.date}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Workshop.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        # Calculate duration from start and end times
        if self.start_time and self.end_time:
            from datetime import datetime, timedelta
            start = datetime.combine(datetime.min, self.start_time)
            end = datetime.combine(datetime.min, self.end_time)
            if end < start:
                end += timedelta(days=1)  # Handle workshops crossing midnight
            duration = (end - start).total_seconds() / 3600
            self.duration_hours = round(duration * 2) / 2  # Round to nearest 0.5

        # Resize image on upload for consistent quality
        process_uploaded_image(self, 'image', max_width=1200, max_height=800)

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('workshops:detail', kwargs={'slug': self.slug})

    @property
    def total_bookings(self):
        return self.current_registrations + self.legacy_bookings

    @property
    def is_full(self):
        return self.total_bookings >= self.max_participants

    @property
    def places_remaining(self):
        return max(0, self.max_participants - self.total_bookings)

    @property
    def is_online(self):
        return self.delivery_method in ['online', 'hybrid']

    @property
    def is_in_person(self):
        return self.delivery_method in ['in_person', 'hybrid']

    def update_registration_count(self):
        """Update current_registrations based on paid registrations."""
        self.current_registrations = self.registrations.filter(
            status__in=['paid', 'attended']
        ).count()
        self.save(update_fields=['current_registrations'])


class WorkshopRegistration(models.Model):
    """Workshop registration (requires user account)."""
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('paid', 'Paid'),
        ('attended', 'Attended'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    workshop = models.ForeignKey(Workshop, on_delete=models.CASCADE, related_name='registrations')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workshop_registrations')

    # Registration details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    phone = models.CharField(max_length=30, blank=True)
    special_requirements = models.TextField(blank=True, help_text="Dietary, accessibility, etc.")

    # In-person workshop fields
    emergency_contact = models.CharField(
        max_length=200,
        blank=True,
        help_text="Emergency contact name and phone number"
    )
    instruments = models.TextField(
        blank=True,
        help_text="What instruments will you be bringing?"
    )

    # Payment
    amount_paid = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    stripe_checkout_session_id = models.CharField(max_length=255, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    # Terms acceptance
    terms_accepted = models.BooleanField(default=False)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)

    # Confirmation
    confirmation_sent = models.BooleanField(default=False)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['workshop', 'user']

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.workshop.title}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update workshop registration count
        self.workshop.update_registration_count()


class WorkshopMaterial(models.Model):
    """Downloadable materials for workshop participants."""
    workshop = models.ForeignKey(Workshop, on_delete=models.CASCADE, related_name='materials')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='workshop_materials/')

    # Access control
    available_before = models.BooleanField(default=True, help_text="Available before the workshop")
    available_after = models.BooleanField(default=True, help_text="Available after the workshop")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return f"{self.workshop.title} - {self.title}"


class WorkshopTerms(models.Model):
    """Workshop terms and conditions (versioned)."""
    version = models.PositiveIntegerField(unique=True)
    content = models.TextField(help_text="Terms and conditions text (supports Markdown)")
    effective_date = models.DateField()
    is_current = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Workshop Terms"
        verbose_name_plural = "Workshop Terms"
        ordering = ['-version']

    def __str__(self):
        status = "CURRENT" if self.is_current else "archived"
        return f"Terms v{self.version} ({status})"

    def save(self, *args, **kwargs):
        if self.is_current:
            # Ensure only one is current
            WorkshopTerms.objects.exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)
