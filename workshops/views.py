import json
import stripe
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.urls import reverse

from .models import Workshop, WorkshopRegistration, WorkshopTerms
from .forms import WorkshopRegistrationForm

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


def index(request):
    """List of upcoming workshops."""
    upcoming_workshops = Workshop.objects.filter(
        status='published',
        date__gte=timezone.now().date()
    ).order_by('date')

    context = {
        'workshops': upcoming_workshops,
    }
    return render(request, 'workshops/index.html', context)


def detail(request, slug):
    """Workshop detail page."""
    workshop = get_object_or_404(Workshop, slug=slug, status='published')

    # Check if user has an active registration (not cancelled or refunded)
    is_registered = False
    registration_status = None
    if request.user.is_authenticated:
        registration = workshop.registrations.filter(user=request.user).first()
        if registration:
            registration_status = registration.status
            is_registered = registration.status in ['paid', 'attended']

    context = {
        'workshop': workshop,
        'is_registered': is_registered,
        'registration_status': registration_status,
    }
    return render(request, 'workshops/detail.html', context)


def register(request, slug):
    """
    Workshop registration - handles both logged-in and new users.
    New users get an account created automatically.
    """
    workshop = get_object_or_404(Workshop, slug=slug, status='published')

    # Staff cannot book workshops
    if request.user.is_authenticated and request.user.is_staff:
        messages.warning(
            request,
            'Staff cannot book workshops or concerts. If you are testing, log off and purchase as a customer.'
        )
        return redirect('workshops:detail', slug=slug)

    # Check capacity
    if workshop.is_full:
        messages.error(request, 'Sorry, this workshop is fully booked.')
        return redirect('workshops:detail', slug=slug)

    # Check if logged-in user has an active registration
    if request.user.is_authenticated:
        if workshop.registrations.filter(user=request.user, status__in=['paid', 'attended']).exists():
            messages.info(request, 'You are already registered for this workshop.')
            return redirect('workshops:detail', slug=slug)

    # Get current terms
    current_terms = WorkshopTerms.objects.filter(is_current=True).first()

    if request.method == 'POST':
        form = WorkshopRegistrationForm(
            request.POST,
            user=request.user if request.user.is_authenticated else None,
            workshop=workshop
        )

        if form.is_valid():
            # Get or create user
            user, created, password = form.get_or_create_user()

            # Check if this user (possibly just created) has an active registration
            if workshop.registrations.filter(user=user, status__in=['paid', 'attended']).exists():
                messages.info(request, 'You are already registered for this workshop.')
                if created:
                    # Log them in if we just created their account
                    login(request, user)
                return redirect('workshops:detail', slug=slug)

            # Store registration data in session for after payment
            request.session['workshop_registration'] = {
                'workshop_id': workshop.id,
                'user_id': user.id,
                'phone': form.cleaned_data.get('phone', ''),
                'special_requirements': form.cleaned_data.get('special_requirements', ''),
                'emergency_contact': form.cleaned_data.get('emergency_contact', ''),
                'instruments': form.cleaned_data.get('instruments', ''),
                'terms_accepted': True,
                'account_created': created,
                'password': password,  # Temporarily store for email
            }

            # Log in the user if we created their account
            if created:
                login(request, user)

            # Create Stripe Checkout Session
            try:
                # Build success/cancel URLs
                success_url = request.build_absolute_uri(
                    reverse('workshops:checkout_success', kwargs={'slug': slug})
                ) + '?session_id={CHECKOUT_SESSION_ID}'
                cancel_url = request.build_absolute_uri(
                    reverse('workshops:checkout_cancel', kwargs={'slug': slug})
                )

                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price_data': {
                            'currency': 'gbp',
                            'unit_amount': int(workshop.price * 100),  # Stripe uses pence
                            'product_data': {
                                'name': workshop.title,
                                'description': f'{workshop.date.strftime("%A, %d %B %Y")} - {workshop.get_delivery_method_display()}',
                            },
                        },
                        'quantity': 1,
                    }],
                    mode='payment',
                    success_url=success_url,
                    cancel_url=cancel_url,
                    customer_email=user.email,
                    payment_intent_data={
                        'description': f'Workshop: {workshop.title} ({workshop.date.strftime("%d %b %Y")})',
                        'metadata': {
                            'type': 'workshop',
                            'workshop_id': str(workshop.id),
                            'workshop_title': workshop.title,
                            'workshop_date': workshop.date.strftime('%Y-%m-%d'),
                            'user_id': str(user.id),
                            'user_email': user.email,
                            'user_name': user.get_full_name(),
                        },
                    },
                    metadata={
                        'type': 'workshop',
                        'workshop_id': str(workshop.id),
                        'workshop_title': workshop.title,
                        'user_id': str(user.id),
                    },
                )

                # Store checkout session ID
                request.session['stripe_checkout_session_id'] = checkout_session.id

                return redirect(checkout_session.url, code=303)

            except stripe.error.StripeError as e:
                messages.error(request, f'Payment error: {str(e)}')
                return redirect('workshops:register', slug=slug)

    else:
        form = WorkshopRegistrationForm(
            user=request.user if request.user.is_authenticated else None,
            workshop=workshop
        )

    context = {
        'workshop': workshop,
        'form': form,
        'terms': current_terms,
    }
    return render(request, 'workshops/register.html', context)


def checkout_success(request, slug):
    """Handle successful Stripe checkout."""
    workshop = get_object_or_404(Workshop, slug=slug)
    session_id = request.GET.get('session_id')

    if not session_id:
        messages.error(request, 'Invalid payment session.')
        return redirect('workshops:detail', slug=slug)

    try:
        # Retrieve the checkout session from Stripe (expand payment_intent)
        checkout_session = stripe.checkout.Session.retrieve(
            session_id,
            expand=['payment_intent']
        )

        if checkout_session.payment_status != 'paid':
            messages.error(request, 'Payment was not completed.')
            return redirect('workshops:detail', slug=slug)

        # Get registration data from session
        reg_data = request.session.get('workshop_registration')
        if not reg_data or reg_data.get('workshop_id') != workshop.id:
            # Try to find existing registration by checkout session
            existing = WorkshopRegistration.objects.filter(
                stripe_checkout_session_id=session_id
            ).first()
            if existing:
                messages.success(request, f'You are registered for {workshop.title}!')
                return redirect('workshops:detail', slug=slug)

            messages.error(request, 'Registration data not found.')
            return redirect('workshops:detail', slug=slug)

        # Check if registration already exists (prevent duplicates)
        from django.contrib.auth.models import User
        user = User.objects.get(id=reg_data['user_id'])

        existing_registration = WorkshopRegistration.objects.filter(
            workshop=workshop,
            user=user
        ).first()

        # Get payment intent ID for refunds
        payment_intent_id = ''
        if hasattr(checkout_session, 'payment_intent'):
            if isinstance(checkout_session.payment_intent, str):
                payment_intent_id = checkout_session.payment_intent
            else:
                payment_intent_id = checkout_session.payment_intent.id

        if existing_registration:
            # Update existing if pending, cancelled, or refunded (re-registration)
            if existing_registration.status in ['pending', 'cancelled', 'refunded']:
                existing_registration.status = 'paid'
                existing_registration.amount_paid = workshop.price
                existing_registration.paid_at = timezone.now()
                existing_registration.stripe_checkout_session_id = session_id
                existing_registration.stripe_payment_intent_id = payment_intent_id
                existing_registration.phone = reg_data.get('phone', '') or existing_registration.phone
                existing_registration.special_requirements = reg_data.get('special_requirements', '') or existing_registration.special_requirements
                existing_registration.emergency_contact = reg_data.get('emergency_contact', '') or existing_registration.emergency_contact
                existing_registration.instruments = reg_data.get('instruments', '') or existing_registration.instruments
                existing_registration.save()

                # Send confirmation email for re-registration
                send_registration_confirmation_email(user, workshop, existing_registration)

            messages.success(request, f'You are registered for {workshop.title}!')
        else:
            # Create the registration
            registration = WorkshopRegistration.objects.create(
                workshop=workshop,
                user=user,
                status='paid',
                phone=reg_data.get('phone', ''),
                special_requirements=reg_data.get('special_requirements', ''),
                emergency_contact=reg_data.get('emergency_contact', ''),
                instruments=reg_data.get('instruments', ''),
                terms_accepted=True,
                terms_accepted_at=timezone.now(),
                amount_paid=workshop.price,
                paid_at=timezone.now(),
                stripe_checkout_session_id=session_id,
                stripe_payment_intent_id=payment_intent_id,
            )

            # Send account creation email if new user
            if reg_data.get('account_created') and reg_data.get('password'):
                send_account_created_email(user, reg_data['password'], workshop)

            # Send confirmation email
            send_registration_confirmation_email(user, workshop, registration)

            messages.success(
                request,
                f'Payment successful! You are registered for {workshop.title}. '
                f'{"An account has been created for you - check your email for login details. " if reg_data.get("account_created") else ""}'
                f'A confirmation email has been sent.'
            )

        # Clear session data
        if 'workshop_registration' in request.session:
            del request.session['workshop_registration']
        if 'stripe_checkout_session_id' in request.session:
            del request.session['stripe_checkout_session_id']

        return redirect('workshops:detail', slug=slug)

    except stripe.error.StripeError as e:
        messages.error(request, f'Error verifying payment: {str(e)}')
        return redirect('workshops:detail', slug=slug)


def checkout_cancel(request, slug):
    """Handle cancelled Stripe checkout."""
    workshop = get_object_or_404(Workshop, slug=slug)

    # Clear session data
    if 'workshop_registration' in request.session:
        del request.session['workshop_registration']
    if 'stripe_checkout_session_id' in request.session:
        del request.session['stripe_checkout_session_id']

    messages.info(request, 'Payment was cancelled. Your registration was not completed.')
    return redirect('workshops:register', slug=slug)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Handle Stripe webhooks for payment confirmation."""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    # If webhook secret is configured, verify signature
    if settings.STRIPE_WEBHOOK_SECRET:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError:
            return HttpResponse(status=400)
    else:
        # For testing without webhook secret
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            return HttpResponse(status=400)

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        # Get metadata
        workshop_id = session.get('metadata', {}).get('workshop_id')
        user_id = session.get('metadata', {}).get('user_id')

        if workshop_id and user_id:
            try:
                from django.contrib.auth.models import User
                workshop = Workshop.objects.get(id=workshop_id)
                user = User.objects.get(id=user_id)

                # Update or find registration
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

    return HttpResponse(status=200)


def send_account_created_email(user, password, workshop):
    """Send email to new user with their account details."""
    subject = f'Your Polyphonica Account - {workshop.title} Registration'

    # Plain text fallback
    plain_message = f"""
Hello {user.first_name},

An account has been created for you on the Polyphonica Recorder Trio website
as part of your registration for: {workshop.title}

Your login details:
Username: {user.username}
Password: {password}

You can log in at: https://polyphonicarecordertrio.com/accounts/login/

We recommend changing your password after logging in.

Best regards,
Polyphonica Recorder Trio
"""

    # HTML message
    html_message = render_to_string('emails/account_created.html', {
        'user': user,
        'password': password,
        'workshop': workshop,
    })

    try:
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=True,
        )
    except Exception:
        pass  # Don't fail registration if email fails


from django.contrib.auth.decorators import login_required
from datetime import timedelta


@login_required
def cancel_registration(request, registration_id):
    """Cancel a workshop registration with appropriate refund."""
    registration = get_object_or_404(
        WorkshopRegistration,
        id=registration_id,
        user=request.user,
        status='paid'
    )

    workshop = registration.workshop
    days_until_workshop = (workshop.date - timezone.now().date()).days

    # Calculate refund based on cancellation policy
    if days_until_workshop >= 7:
        refund_percent = 100
        refund_message = "Full refund"
    else:
        refund_percent = 0
        refund_message = "No refund available (cancellation less than 7 days before workshop)"

    if request.method == 'POST':
        confirm = request.POST.get('confirm') == 'yes'

        if not confirm:
            messages.info(request, 'Cancellation was not confirmed.')
            return redirect('accounts:profile')

        try:
            refund_amount = 0

            # Process refund if applicable and payment intent exists
            if refund_percent > 0 and registration.stripe_payment_intent_id:
                refund_amount = int(float(registration.amount_paid) * 100 * refund_percent / 100)

                refund = stripe.Refund.create(
                    payment_intent=registration.stripe_payment_intent_id,
                    amount=refund_amount,
                    metadata={
                        'type': 'workshop_cancellation',
                        'workshop_id': str(workshop.id),
                        'workshop_title': workshop.title,
                        'registration_id': str(registration.id),
                        'refund_percent': str(refund_percent),
                    }
                )

            # Update registration status
            registration.status = 'refunded' if refund_percent > 0 else 'cancelled'
            registration.save()

            # Send cancellation email
            send_cancellation_email(registration, refund_percent, refund_amount / 100 if refund_amount else 0)

            if refund_percent == 100:
                messages.success(
                    request,
                    f'Your registration for {workshop.title} has been cancelled. '
                    f'A full refund of £{registration.amount_paid} will be processed.'
                )
            else:
                messages.success(
                    request,
                    f'Your registration for {workshop.title} has been cancelled. '
                    f'No refund is available for cancellations less than 7 days before the workshop.'
                )

            return redirect('accounts:profile')

        except stripe.error.StripeError as e:
            messages.error(request, f'Error processing refund: {str(e)}')
            return redirect('accounts:profile')

    # GET request - show confirmation page
    context = {
        'registration': registration,
        'workshop': workshop,
        'days_until_workshop': days_until_workshop,
        'refund_percent': refund_percent,
        'refund_message': refund_message,
        'refund_amount': float(registration.amount_paid) * refund_percent / 100,
    }
    return render(request, 'workshops/cancel_registration.html', context)


def send_cancellation_email(registration, refund_percent, refund_amount):
    """Send cancellation confirmation email."""
    workshop = registration.workshop
    user = registration.user
    subject = f'Registration Cancelled - {workshop.title}'

    # Plain text fallback
    refund_text = ""
    if refund_percent == 100:
        refund_text = f"A full refund of £{refund_amount:.2f} will be processed to your original payment method within 5-10 business days."
    else:
        refund_text = "As this cancellation was made less than 7 days before the workshop, no refund is available per our cancellation policy."

    plain_message = f"""
Hello {user.first_name},

Your registration for the following workshop has been cancelled:

{workshop.title}
Date: {workshop.date.strftime('%A, %d %B %Y')}
Time: {workshop.start_time.strftime('%I:%M %p')} - {workshop.end_time.strftime('%I:%M %p')}

{refund_text}

Best regards,
Polyphonica Recorder Trio
"""

    # HTML message
    html_message = render_to_string('emails/cancellation_confirmation.html', {
        'user': user,
        'workshop': workshop,
        'registration': registration,
        'refund_percent': refund_percent,
        'refund_amount': refund_amount,
    })

    try:
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=True,
        )
    except Exception:
        pass


def send_registration_confirmation_email(user, workshop, registration):
    """Send workshop registration confirmation email."""
    subject = f'Registration Confirmed - {workshop.title}'

    # Plain text fallback
    location_info = ""
    if workshop.is_in_person and workshop.venue_name:
        location_info = f"Venue: {workshop.venue_name}, {workshop.venue_address}, {workshop.venue_postcode}"
    if workshop.is_online:
        location_info += "\nOnline access details will be sent closer to the workshop date."

    plain_message = f"""
Hello {user.first_name},

Thank you for registering for our workshop!

{workshop.title}
Date: {workshop.date.strftime('%A, %d %B %Y')}
Time: {workshop.start_time.strftime('%I:%M %p')} - {workshop.end_time.strftime('%I:%M %p')}
{location_info}

Amount paid: £{registration.amount_paid}

We look forward to seeing you!

Best regards,
Polyphonica Recorder Trio
"""

    # HTML message
    html_message = render_to_string('emails/registration_confirmation.html', {
        'user': user,
        'workshop': workshop,
        'registration': registration,
    })

    try:
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=True,
        )
        # Mark confirmation as sent
        registration.confirmation_sent = True
        registration.save(update_fields=['confirmation_sent'])
    except Exception:
        pass
