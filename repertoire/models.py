from django.db import models
from django.urls import reverse


class Composer(models.Model):
    """Composer in the repertoire library."""
    name = models.CharField(max_length=200)
    birth_year = models.PositiveIntegerField(null=True, blank=True)
    death_year = models.PositiveIntegerField(null=True, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True, help_text="Biography for programme notes")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        """Name with dates if available."""
        if self.birth_year and self.death_year:
            return f"{self.name} ({self.birth_year}–{self.death_year})"
        elif self.birth_year:
            return f"{self.name} (b. {self.birth_year})"
        return self.name

    @property
    def dates_display(self):
        """Just the dates for display."""
        if self.birth_year and self.death_year:
            return f"({self.birth_year}–{self.death_year})"
        elif self.birth_year:
            return f"(b. {self.birth_year})"
        return ""


class Piece(models.Model):
    """Musical piece in the repertoire library."""
    title = models.CharField(max_length=300)
    composer = models.ForeignKey(
        Composer,
        on_delete=models.CASCADE,
        related_name='pieces'
    )
    duration = models.PositiveIntegerField(
        help_text="Duration in minutes"
    )
    catalogue_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="e.g., BWV 1079, Op. 10"
    )
    instrumentation = models.CharField(
        max_length=200,
        blank=True,
        help_text="e.g., Alto, Tenor, Bass recorders"
    )
    notes = models.TextField(
        blank=True,
        help_text="Programme notes about this piece"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['composer__name', 'title']

    def __str__(self):
        if self.catalogue_number:
            return f"{self.title}, {self.catalogue_number} - {self.composer.name}"
        return f"{self.title} - {self.composer.name}"

    @property
    def duration_display(self):
        """Format duration for display."""
        if self.duration >= 60:
            hours = self.duration // 60
            mins = self.duration % 60
            if mins:
                return f"{hours}h {mins}m"
            return f"{hours}h"
        return f"{self.duration}m"


class Programme(models.Model):
    """Concert programme - a collection of pieces, talks, and intervals."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('final', 'Final'),
    ]

    title = models.CharField(max_length=200)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    notes = models.TextField(
        blank=True,
        help_text="Internal notes about this programme"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    def get_absolute_url(self):
        return reverse('repertoire:programme_detail', kwargs={'pk': self.pk})

    @property
    def total_duration(self):
        """Calculate total programme duration in minutes."""
        total = 0
        for item in self.items.all():
            total += item.duration or 0
        return total

    @property
    def total_duration_display(self):
        """Format total duration for display."""
        total = self.total_duration
        if total >= 60:
            hours = total // 60
            mins = total % 60
            if mins:
                return f"{hours}h {mins}m"
            return f"{hours}h"
        return f"{total}m"

    @property
    def piece_count(self):
        """Count of pieces (excluding talks and intervals)."""
        return self.items.filter(item_type='piece').count()


class ProgrammeItem(models.Model):
    """An item in a programme - piece, talk, or interval."""
    ITEM_TYPE_CHOICES = [
        ('piece', 'Piece'),
        ('talk', 'Talk'),
        ('interval', 'Interval'),
    ]

    programme = models.ForeignKey(
        Programme,
        on_delete=models.CASCADE,
        related_name='items'
    )
    order = models.PositiveIntegerField(default=0)
    item_type = models.CharField(
        max_length=20,
        choices=ITEM_TYPE_CHOICES,
        default='piece'
    )

    # For piece items
    piece = models.ForeignKey(
        Piece,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='programme_items'
    )

    # For talk/interval items
    title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Title for talk or interval (e.g., 'Introduction', 'Interval')"
    )
    talk_text = models.TextField(
        blank=True,
        help_text="Text/notes for what to say during the talk"
    )

    # Duration override for talks/intervals (pieces use their own duration)
    custom_duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Duration in minutes (for talks/intervals)"
    )

    # Internal notes
    notes = models.TextField(
        blank=True,
        help_text="Internal notes about this item"
    )

    class Meta:
        ordering = ['order']

    def __str__(self):
        if self.item_type == 'piece' and self.piece:
            return f"{self.piece.title}"
        return self.title or self.get_item_type_display()

    @property
    def duration(self):
        """Get duration based on item type."""
        if self.item_type == 'piece' and self.piece:
            return self.piece.duration
        return self.custom_duration or 0

    @property
    def duration_display(self):
        """Format duration for display."""
        d = self.duration
        if d >= 60:
            hours = d // 60
            mins = d % 60
            if mins:
                return f"{hours}h {mins}m"
            return f"{hours}h"
        return f"{d}m" if d else "—"
