from django.shortcuts import render
from .models import MediaItem


def index(request):
    """Media page with audio, video, and image content."""
    videos = MediaItem.objects.filter(
        is_published=True,
        media_type='video'
    ).order_by('-is_featured', 'display_order', '-date_added')

    audio = MediaItem.objects.filter(
        is_published=True,
        media_type='audio'
    ).order_by('-is_featured', 'display_order', '-date_added')

    images = MediaItem.objects.filter(
        is_published=True,
        media_type='image'
    ).order_by('-is_featured', 'display_order', '-date_added')

    context = {
        'videos': videos,
        'audio': audio,
        'images': images,
    }
    return render(request, 'media_content/index.html', context)
