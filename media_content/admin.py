from django.contrib import admin
from .models import MediaItem


@admin.register(MediaItem)
class MediaItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'media_type', 'category', 'is_featured', 'is_published', 'display_order']
    list_filter = ['media_type', 'is_featured', 'is_published', 'category']
    list_editable = ['is_featured', 'is_published', 'display_order']
    search_fields = ['title', 'description']
    ordering = ['-is_featured', 'display_order', '-date_added']

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'media_type', 'thumbnail')
        }),
        ('Video', {
            'fields': ('video_url', 'video_embed_code'),
            'classes': ('collapse',)
        }),
        ('Audio', {
            'fields': ('audio_file', 'audio_url'),
            'classes': ('collapse',)
        }),
        ('Organization', {
            'fields': ('category', 'performance_date', 'display_order')
        }),
        ('Display', {
            'fields': ('is_featured', 'is_published')
        }),
    )
