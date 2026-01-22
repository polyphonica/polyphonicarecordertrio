from django.db import models


class MediaItem(models.Model):
    """Audio and video media items."""
    MEDIA_TYPE_CHOICES = [
        ('video', 'Video'),
        ('audio', 'Audio'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES)

    # For videos (YouTube, Vimeo embeds)
    video_url = models.URLField(blank=True, help_text="YouTube or Vimeo URL")
    video_embed_code = models.TextField(blank=True, help_text="Custom embed code (optional)")

    # For audio
    audio_file = models.FileField(upload_to='audio/', blank=True, null=True)
    audio_url = models.URLField(blank=True, help_text="External audio URL (SoundCloud, etc.)")

    # Thumbnail
    thumbnail = models.ImageField(upload_to='media_thumbnails/', blank=True, null=True)

    # Organization
    category = models.CharField(max_length=100, blank=True, help_text="e.g., 'Live Performance', 'Studio Recording'")
    performance_date = models.DateField(blank=True, null=True)

    # Display
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    # Metadata
    date_added = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Media Item"
        verbose_name_plural = "Media Items"
        ordering = ['-is_featured', 'display_order', '-date_added']

    def __str__(self):
        return f"{self.title} ({self.get_media_type_display()})"

    @property
    def youtube_video_id(self):
        """Extract YouTube video ID from URL."""
        if 'youtube.com' in self.video_url:
            # Handle youtube.com/watch?v=VIDEO_ID
            if 'v=' in self.video_url:
                return self.video_url.split('v=')[1].split('&')[0]
        elif 'youtu.be' in self.video_url:
            # Handle youtu.be/VIDEO_ID
            return self.video_url.split('/')[-1].split('?')[0]
        return None

    @property
    def vimeo_video_id(self):
        """Extract Vimeo video ID from URL."""
        if 'vimeo.com' in self.video_url:
            return self.video_url.split('/')[-1].split('?')[0]
        return None
