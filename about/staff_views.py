from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django import forms
from django.db.models import Max

from .models import TrioInfo, PlayerBio


class TrioInfoForm(forms.ModelForm):
    """Form for editing trio information."""

    class Meta:
        model = TrioInfo
        fields = ['name', 'tagline', 'description', 'hero_image']
        widgets = {
            'tagline': forms.TextInput(attrs={'class': 'w-full'}),
            'description': forms.Textarea(attrs={'rows': 8}),
        }


class PlayerBioForm(forms.ModelForm):
    """Form for creating/editing player biographies."""

    class Meta:
        model = PlayerBio
        fields = ['name', 'bio', 'photo', 'website', 'display_order', 'is_active']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 5}),
        }


@staff_member_required
def about_edit(request):
    """Edit the About Polyphonica content."""
    # Get or create the singleton TrioInfo
    trio_info = TrioInfo.objects.first()
    if not trio_info:
        trio_info = TrioInfo(name="Polyphonica Recorder Trio")

    if request.method == 'POST':
        form = TrioInfoForm(request.POST, request.FILES, instance=trio_info)
        if form.is_valid():
            form.save()
            messages.success(request, 'About content updated successfully.')
            return redirect('about:staff_about_edit')
    else:
        form = TrioInfoForm(instance=trio_info)

    context = {
        'form': form,
        'trio_info': trio_info,
    }
    return render(request, 'about/staff/about_form.html', context)


@staff_member_required
def player_list(request):
    """List all players for staff management."""
    players = PlayerBio.objects.all().order_by('display_order', 'name')

    context = {
        'players': players,
    }
    return render(request, 'about/staff/player_list.html', context)


@staff_member_required
def player_create(request):
    """Create a new player biography."""
    if request.method == 'POST':
        form = PlayerBioForm(request.POST, request.FILES)
        if form.is_valid():
            player = form.save()
            messages.success(request, f'Player "{player.name}" created successfully.')
            return redirect('about:staff_player_list')
    else:
        # Set default display_order to next available
        max_order = PlayerBio.objects.aggregate(max_order=Max('display_order'))['max_order'] or 0
        form = PlayerBioForm(initial={'display_order': max_order + 1})

    context = {
        'form': form,
        'action': 'Add',
    }
    return render(request, 'about/staff/player_form.html', context)


@staff_member_required
def player_edit(request, pk):
    """Edit an existing player biography."""
    player = get_object_or_404(PlayerBio, pk=pk)

    if request.method == 'POST':
        form = PlayerBioForm(request.POST, request.FILES, instance=player)
        if form.is_valid():
            form.save()
            messages.success(request, f'Player "{player.name}" updated successfully.')
            return redirect('about:staff_player_list')
    else:
        form = PlayerBioForm(instance=player)

    context = {
        'form': form,
        'player': player,
        'action': 'Edit',
    }
    return render(request, 'about/staff/player_form.html', context)


@staff_member_required
def player_delete(request, pk):
    """Delete a player biography."""
    player = get_object_or_404(PlayerBio, pk=pk)

    if request.method == 'POST':
        name = player.name
        player.delete()
        messages.success(request, f'Player "{name}" deleted.')
        return redirect('about:staff_player_list')

    context = {
        'player': player,
    }
    return render(request, 'about/staff/player_delete.html', context)
