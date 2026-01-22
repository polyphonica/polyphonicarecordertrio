from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django import forms

from .models import Workshop, WorkshopRegistration, WorkshopTerms


class WorkshopForm(forms.ModelForm):
    """Form for creating/editing workshops."""

    class Meta:
        model = Workshop
        fields = [
            'title', 'description', 'short_description',
            'date', 'start_time', 'end_time', 'duration_hours',
            'delivery_method',
            'venue_name', 'venue_address', 'venue_postcode', 'venue_map_link',
            'meeting_link', 'meeting_password',
            'prerequisites', 'materials_needed',
            'image',
            'price', 'max_participants',
            'status',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'short_description': forms.Textarea(attrs={'rows': 2}),
            'prerequisites': forms.Textarea(attrs={'rows': 3}),
            'materials_needed': forms.Textarea(attrs={'rows': 3}),
            'venue_address': forms.Textarea(attrs={'rows': 2}),
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }


@staff_member_required
def workshop_list(request):
    """List all workshops for staff."""
    upcoming = Workshop.objects.filter(date__gte=timezone.now().date()).order_by('date')
    past = Workshop.objects.filter(date__lt=timezone.now().date()).order_by('-date')[:20]

    context = {
        'upcoming_workshops': upcoming,
        'past_workshops': past,
    }
    return render(request, 'workshops/staff/workshop_list.html', context)


@staff_member_required
def workshop_create(request):
    """Create a new workshop."""
    if request.method == 'POST':
        form = WorkshopForm(request.POST, request.FILES)
        if form.is_valid():
            workshop = form.save()
            messages.success(request, f'Workshop "{workshop.title}" created successfully.')
            return redirect('workshops:staff_workshop_list')
    else:
        form = WorkshopForm()

    context = {
        'form': form,
        'action': 'Create',
    }
    return render(request, 'workshops/staff/workshop_form.html', context)


@staff_member_required
def workshop_edit(request, pk):
    """Edit an existing workshop."""
    workshop = get_object_or_404(Workshop, pk=pk)

    if request.method == 'POST':
        form = WorkshopForm(request.POST, request.FILES, instance=workshop)
        if form.is_valid():
            form.save()
            messages.success(request, f'Workshop "{workshop.title}" updated successfully.')
            return redirect('workshops:staff_workshop_list')
    else:
        form = WorkshopForm(instance=workshop)

    context = {
        'form': form,
        'workshop': workshop,
        'action': 'Edit',
    }
    return render(request, 'workshops/staff/workshop_form.html', context)


@staff_member_required
def workshop_attendees(request, pk):
    """View attendees for a workshop."""
    workshop = get_object_or_404(Workshop, pk=pk)

    registrations = WorkshopRegistration.objects.filter(
        workshop=workshop
    ).select_related('user').order_by('created_at')

    # Filter by status if provided
    status_filter = request.GET.get('status', '')
    if status_filter:
        registrations = registrations.filter(status=status_filter)

    context = {
        'workshop': workshop,
        'registrations': registrations,
        'status_filter': status_filter,
        'status_choices': WorkshopRegistration.STATUS_CHOICES,
    }
    return render(request, 'workshops/staff/workshop_attendees.html', context)


@staff_member_required
def workshop_delete(request, pk):
    """Delete a workshop."""
    workshop = get_object_or_404(Workshop, pk=pk)

    if request.method == 'POST':
        title = workshop.title
        workshop.delete()
        messages.success(request, f'Workshop "{title}" deleted.')
        return redirect('workshops:staff_workshop_list')

    context = {
        'workshop': workshop,
    }
    return render(request, 'workshops/staff/workshop_delete.html', context)
