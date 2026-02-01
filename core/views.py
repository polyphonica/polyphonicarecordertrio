import urllib.request
import urllib.parse
import json

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.db import models
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


def verify_turnstile(token):
    """Verify Cloudflare Turnstile token."""
    if not settings.TURNSTILE_SECRET_KEY:
        # If no secret key configured, skip verification (for development)
        return True

    try:
        url = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
        data = urllib.parse.urlencode({
            'secret': settings.TURNSTILE_SECRET_KEY,
            'response': token,
        }).encode()

        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())

        return result.get('success', False)
    except Exception:
        # If verification fails, allow submission (fail open for usability)
        return True


def home(request):
    """Home page with hero image and upcoming events."""
    from concerts.models import Concert
    from workshops.models import Workshop

    # Get upcoming concerts and workshops for highlights
    upcoming_concerts = Concert.objects.filter(
        status='published'
    ).order_by('date')[:3]

    upcoming_workshops = Workshop.objects.filter(
        status='published'
    ).order_by('date')[:3]

    context = {
        'upcoming_concerts': upcoming_concerts,
        'upcoming_workshops': upcoming_workshops,
    }
    return render(request, 'core/home.html', context)


def privacy(request):
    """Privacy policy page."""
    return render(request, 'core/privacy.html')


def accessibility(request):
    """Accessibility statement page."""
    return render(request, 'core/accessibility.html')


def contact(request):
    """Contact page with contact form."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()
        turnstile_token = request.POST.get('cf-turnstile-response', '')

        # Verify Turnstile
        if not verify_turnstile(turnstile_token):
            messages.error(request, 'Spam verification failed. Please try again.')
            return render(request, 'core/contact.html', {
                'turnstile_site_key': settings.TURNSTILE_SITE_KEY,
            })

        if name and email and message:
            # Send email
            full_subject = f"Contact Form: {subject}" if subject else "Contact Form Submission"
            email_body = f"From: {name} <{email}>\n\n{message}"

            try:
                send_mail(
                    full_subject,
                    email_body,
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.CONTACT_EMAIL],
                    fail_silently=False,
                )
                messages.success(request, 'Thank you for your message. We will be in touch soon.')
                return redirect('core:contact')
            except Exception:
                messages.error(request, 'Sorry, there was an error sending your message. Please try again.')
        else:
            messages.error(request, 'Please fill in all required fields.')

    return render(request, 'core/contact.html', {
        'turnstile_site_key': settings.TURNSTILE_SITE_KEY,
    })


@staff_member_required
def staff_dashboard(request):
    """Staff dashboard with overview of upcoming events."""
    from concerts.models import Concert, ConcertTicketOrder
    from workshops.models import Workshop, WorkshopRegistration

    today = timezone.now().date()

    # Upcoming workshops
    upcoming_workshops = Workshop.objects.filter(
        date__gte=today
    ).order_by('date')[:5]

    # Upcoming concerts
    upcoming_concerts = Concert.objects.filter(
        date__gte=today
    ).order_by('date')[:5]

    # Recent registrations
    recent_workshop_registrations = WorkshopRegistration.objects.filter(
        status='paid'
    ).select_related('workshop', 'user').order_by('-created_at')[:10]

    # Recent ticket orders
    recent_ticket_orders = ConcertTicketOrder.objects.filter(
        status='paid'
    ).select_related('concert').order_by('-created_at')[:10]

    # Stats
    total_workshop_registrations = WorkshopRegistration.objects.filter(
        status='paid',
        workshop__date__gte=today
    ).count()

    total_tickets_sold = ConcertTicketOrder.objects.filter(
        status='paid',
        concert__date__gte=today
    ).aggregate(total=models.Sum('quantity'))['total'] or 0

    context = {
        'upcoming_workshops': upcoming_workshops,
        'upcoming_concerts': upcoming_concerts,
        'recent_workshop_registrations': recent_workshop_registrations,
        'recent_ticket_orders': recent_ticket_orders,
        'total_workshop_registrations': total_workshop_registrations,
        'total_tickets_sold': total_tickets_sold,
    }
    return render(request, 'core/staff_dashboard.html', context)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Unified Stripe webhook handler for all payment types.
    Handles both workshop registrations and concert ticket orders.
    """
    from core.stripe_utils import verify_webhook
    from workshops.models import Workshop, WorkshopRegistration
    from concerts.models import Concert, ConcertTicketOrder
    from django.contrib.auth.models import User

    event, error_response = verify_webhook(request)
    if error_response:
        return error_response

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        metadata = session.get('metadata', {})
        payment_type = metadata.get('type')

        if payment_type == 'workshop':
            # Handle workshop registration payment
            workshop_id = metadata.get('workshop_id')
            user_id = metadata.get('user_id')

            if workshop_id and user_id:
                try:
                    workshop = Workshop.objects.get(id=workshop_id)
                    user = User.objects.get(id=user_id)

                    registration = WorkshopRegistration.objects.filter(
                        workshop=workshop,
                        user=user
                    ).first()

                    if registration and registration.status == 'pending':
                        registration.status = 'paid'
                        registration.amount_paid = workshop.price
                        registration.paid_at = timezone.now()
                        registration.stripe_checkout_session_id = session.get('id', '')
                        registration.save()

                except (Workshop.DoesNotExist, User.DoesNotExist):
                    pass

        elif payment_type == 'concert':
            # Handle concert ticket payment
            concert_id = metadata.get('concert_id')

            if concert_id:
                order = ConcertTicketOrder.objects.filter(
                    stripe_checkout_session_id=session.get('id', ''),
                    status='pending'
                ).first()

                if order:
                    order.status = 'paid'
                    order.paid_at = timezone.now()
                    order.save()

                    # Update tickets sold
                    order.concert.tickets_sold += order.quantity
                    order.concert.save(update_fields=['tickets_sold'])

    return HttpResponse(status=200)
