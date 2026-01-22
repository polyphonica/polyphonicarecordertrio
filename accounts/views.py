from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegistrationForm


def register(request):
    """User registration for workshop bookings."""
    if request.user.is_authenticated:
        return redirect('accounts:profile')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Welcome! Your account has been created.')
            return redirect('core:home')
    else:
        form = UserRegistrationForm()

    context = {
        'form': form,
    }
    return render(request, 'accounts/register.html', context)


@login_required
def profile(request):
    """User profile page with booking history."""
    from workshops.models import WorkshopRegistration
    from django.utils import timezone

    registrations = WorkshopRegistration.objects.filter(
        user=request.user
    ).select_related('workshop').order_by('-created_at')

    context = {
        'registrations': registrations,
        'today': timezone.now().date(),
    }
    return render(request, 'accounts/profile.html', context)
