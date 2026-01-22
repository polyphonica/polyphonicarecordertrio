from django.db import models


class TrioInfo(models.Model):
    """General information about the trio (singleton)."""
    name = models.CharField(max_length=200, default="Polyphonica Recorder Trio")
    tagline = models.CharField(max_length=300, blank=True)
    description = models.TextField(help_text="Main description of the trio")
    history = models.TextField(blank=True, help_text="History and background")
    hero_image = models.ImageField(upload_to='about/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Trio Information"
        verbose_name_plural = "Trio Information"

    def __str__(self):
        return self.name


class PlayerBio(models.Model):
    """Individual player biographies."""
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=100, blank=True, help_text="e.g., 'Soprano & Alto Recorders'")
    bio = models.TextField(help_text="Player biography")
    photo = models.ImageField(upload_to='players/', blank=True, null=True)
    website = models.URLField(blank=True)
    display_order = models.PositiveIntegerField(default=0, help_text="Order in which to display")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Player Biography"
        verbose_name_plural = "Player Biographies"
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name
