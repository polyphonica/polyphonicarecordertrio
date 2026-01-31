from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django import forms

from .models import MediaItem


class MediaItemForm(forms.ModelForm):
    """Form for creating/editing media items."""

    class Meta:
        model = MediaItem
        fields = [
            'title', 'description', 'media_type',
            'video_url', 'video_embed_code',
            'audio_file', 'audio_url',
            'image_file', 'caption',
            'thumbnail',
            'category', 'performance_date',
            'is_featured', 'is_published', 'display_order',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'video_embed_code': forms.Textarea(attrs={'rows': 3}),
            'performance_date': forms.DateInput(attrs={'type': 'date'}),
        }


@staff_member_required
def media_list(request):
    """List all media items for staff."""
    media_type_filter = request.GET.get('type', '')

    media_items = MediaItem.objects.all().order_by('-is_featured', 'display_order', '-date_added')

    if media_type_filter:
        media_items = media_items.filter(media_type=media_type_filter)

    # Group by type for display
    videos = MediaItem.objects.filter(media_type='video').order_by('-is_featured', 'display_order', '-date_added')
    audio = MediaItem.objects.filter(media_type='audio').order_by('-is_featured', 'display_order', '-date_added')
    images = MediaItem.objects.filter(media_type='image').order_by('-is_featured', 'display_order', '-date_added')

    context = {
        'videos': videos,
        'audio': audio,
        'images': images,
        'media_type_filter': media_type_filter,
    }
    return render(request, 'media_content/staff/media_list.html', context)


@staff_member_required
def media_create(request):
    """Create a new media item."""
    if request.method == 'POST':
        form = MediaItemForm(request.POST, request.FILES)
        if form.is_valid():
            media_item = form.save()
            messages.success(request, f'{media_item.get_media_type_display()} "{media_item.title}" created successfully.')
            return redirect('media_content:staff_media_list')
    else:
        # Pre-select media type if provided in query string
        initial = {}
        media_type = request.GET.get('type')
        if media_type in ['video', 'audio', 'image']:
            initial['media_type'] = media_type
        form = MediaItemForm(initial=initial)

    context = {
        'form': form,
        'action': 'Create',
    }
    return render(request, 'media_content/staff/media_form.html', context)


@staff_member_required
def media_edit(request, pk):
    """Edit an existing media item."""
    media_item = get_object_or_404(MediaItem, pk=pk)

    if request.method == 'POST':
        form = MediaItemForm(request.POST, request.FILES, instance=media_item)
        if form.is_valid():
            form.save()
            messages.success(request, f'{media_item.get_media_type_display()} "{media_item.title}" updated successfully.')
            return redirect('media_content:staff_media_list')
    else:
        form = MediaItemForm(instance=media_item)

    context = {
        'form': form,
        'media_item': media_item,
        'action': 'Edit',
    }
    return render(request, 'media_content/staff/media_form.html', context)


@staff_member_required
def media_delete(request, pk):
    """Delete a media item."""
    media_item = get_object_or_404(MediaItem, pk=pk)

    if request.method == 'POST':
        title = media_item.title
        media_type = media_item.get_media_type_display()
        # Delete associated files
        if media_item.audio_file:
            media_item.audio_file.delete()
        if media_item.image_file:
            media_item.image_file.delete()
        if media_item.thumbnail:
            media_item.thumbnail.delete()
        media_item.delete()
        messages.success(request, f'{media_type} "{title}" deleted.')
        return redirect('media_content:staff_media_list')

    context = {
        'media_item': media_item,
    }
    return render(request, 'media_content/staff/media_delete.html', context)
