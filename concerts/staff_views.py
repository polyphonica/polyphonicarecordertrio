from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django import forms

from .models import Concert, ConcertTicketOrder


class ConcertForm(forms.ModelForm):
    """Form for creating/editing concerts."""

    class Meta:
        model = Concert
        fields = [
            'title', 'description',
            'date', 'time', 'doors_open',
            'venue_name', 'venue_address', 'venue_postcode', 'venue_map_link',
            'image',
            'ticket_source', 'external_ticket_url',
            'full_price', 'discount_price', 'discount_label',
            'capacity',
            'status',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'venue_address': forms.Textarea(attrs={'rows': 2}),
            'date': forms.DateInput(attrs={'type': 'date'}),
            'time': forms.TimeInput(attrs={'type': 'time'}),
            'doors_open': forms.TimeInput(attrs={'type': 'time'}),
        }


@staff_member_required
def concert_list(request):
    """List all concerts for staff."""
    upcoming = Concert.objects.filter(date__gte=timezone.now().date()).order_by('date')
    past = Concert.objects.filter(date__lt=timezone.now().date()).order_by('-date')[:20]

    context = {
        'upcoming_concerts': upcoming,
        'past_concerts': past,
    }
    return render(request, 'concerts/staff/concert_list.html', context)


@staff_member_required
def concert_create(request):
    """Create a new concert."""
    if request.method == 'POST':
        form = ConcertForm(request.POST, request.FILES)
        if form.is_valid():
            concert = form.save()
            messages.success(request, f'Concert "{concert.title}" created successfully.')
            return redirect('concerts:staff_concert_list')
    else:
        form = ConcertForm()

    context = {
        'form': form,
        'action': 'Create',
    }
    return render(request, 'concerts/staff/concert_form.html', context)


@staff_member_required
def concert_edit(request, pk):
    """Edit an existing concert."""
    concert = get_object_or_404(Concert, pk=pk)

    if request.method == 'POST':
        form = ConcertForm(request.POST, request.FILES, instance=concert)
        if form.is_valid():
            form.save()
            messages.success(request, f'Concert "{concert.title}" updated successfully.')
            return redirect('concerts:staff_concert_list')
    else:
        form = ConcertForm(instance=concert)

    context = {
        'form': form,
        'concert': concert,
        'action': 'Edit',
    }
    return render(request, 'concerts/staff/concert_form.html', context)


@staff_member_required
def concert_orders(request, pk):
    """View ticket orders for a concert."""
    concert = get_object_or_404(Concert, pk=pk)

    orders = ConcertTicketOrder.objects.filter(
        concert=concert
    ).order_by('-created_at')

    # Filter by status if provided
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(status=status_filter)

    context = {
        'concert': concert,
        'orders': orders,
        'status_filter': status_filter,
        'status_choices': ConcertTicketOrder.STATUS_CHOICES,
        'total_tickets': sum(o.quantity for o in orders.filter(status='paid')),
    }
    return render(request, 'concerts/staff/concert_orders.html', context)


@staff_member_required
def concert_delete(request, pk):
    """Delete a concert."""
    concert = get_object_or_404(Concert, pk=pk)

    if request.method == 'POST':
        title = concert.title
        concert.delete()
        messages.success(request, f'Concert "{title}" deleted.')
        return redirect('concerts:staff_concert_list')

    context = {
        'concert': concert,
    }
    return render(request, 'concerts/staff/concert_delete.html', context)
