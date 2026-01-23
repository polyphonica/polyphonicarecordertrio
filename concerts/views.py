import json
import stripe
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.urls import reverse

from .models import Concert, ConcertTicketOrder
from .forms import ConcertTicketOrderForm

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


def index(request):
    """List of upcoming concerts."""
    upcoming_concerts = Concert.objects.filter(
        status='published',
        date__gte=timezone.now().date()
    ).order_by('date')

    past_concerts = Concert.objects.filter(
        status='published',
        date__lt=timezone.now().date()
    ).order_by('-date')[:10]

    context = {
        'upcoming_concerts': upcoming_concerts,
        'past_concerts': past_concerts,
    }
    return render(request, 'concerts/index.html', context)


def detail(request, slug):
    """Concert detail page."""
    concert = get_object_or_404(Concert, slug=slug, status='published')

    context = {
        'concert': concert,
    }
    return render(request, 'concerts/detail.html', context)


def order_tickets(request, slug):
    """Order tickets for a concert (guest checkout)."""
    concert = get_object_or_404(Concert, slug=slug, status='published')

    # Staff cannot book concerts
    if request.user.is_authenticated and request.user.is_staff:
        messages.warning(
            request,
            'Staff cannot book workshops or concerts. If you are testing, log off and purchase as a customer.'
        )
        return redirect('concerts:detail', slug=slug)

    # Only allow internal ticket sales
    if concert.ticket_source != 'internal':
        messages.error(request, 'Tickets for this concert are not available here.')
        return redirect('concerts:detail', slug=slug)

    # Check if sold out
    if concert.is_sold_out:
        messages.error(request, 'Sorry, this concert is sold out.')
        return redirect('concerts:detail', slug=slug)

    if request.method == 'POST':
        form = ConcertTicketOrderForm(request.POST, concert=concert)

        if form.is_valid():
            # Calculate prices
            unit_price = form.get_unit_price()
            total_price = form.get_total_price()
            quantity = form.cleaned_data['quantity']
            ticket_type = form.cleaned_data['ticket_type']

            # Store order data in session
            request.session['concert_order'] = {
                'concert_id': concert.id,
                'name': form.cleaned_data['name'],
                'email': form.cleaned_data['email'],
                'phone': form.cleaned_data.get('phone', ''),
                'ticket_type': ticket_type,
                'quantity': quantity,
                'unit_price': str(unit_price),
                'total_price': str(total_price),
            }

            # Create Stripe Checkout Session
            try:
                # Build ticket description
                ticket_label = 'Full Price' if ticket_type == 'full' else concert.discount_label

                success_url = request.build_absolute_uri(
                    reverse('concerts:checkout_success', kwargs={'slug': slug})
                ) + '?session_id={CHECKOUT_SESSION_ID}'
                cancel_url = request.build_absolute_uri(
                    reverse('concerts:checkout_cancel', kwargs={'slug': slug})
                )

                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price_data': {
                            'currency': 'gbp',
                            'unit_amount': int(unit_price * 100),
                            'product_data': {
                                'name': f'{concert.title} - {ticket_label}',
                                'description': f'{concert.date.strftime("%A, %d %B %Y")} at {concert.venue_name}',
                            },
                        },
                        'quantity': quantity,
                    }],
                    mode='payment',
                    success_url=success_url,
                    cancel_url=cancel_url,
                    customer_email=form.cleaned_data['email'],
                    payment_intent_data={
                        'description': f'Concert: {concert.title} ({concert.date.strftime("%d %b %Y")}) - {quantity}x {ticket_label}',
                        'metadata': {
                            'type': 'concert',
                            'concert_id': str(concert.id),
                            'concert_title': concert.title,
                            'concert_date': concert.date.strftime('%Y-%m-%d'),
                            'venue': concert.venue_name,
                            'ticket_type': ticket_type,
                            'quantity': str(quantity),
                            'customer_email': form.cleaned_data['email'],
                            'customer_name': form.cleaned_data['name'],
                        },
                    },
                    metadata={
                        'type': 'concert',
                        'concert_id': str(concert.id),
                        'concert_title': concert.title,
                        'ticket_type': ticket_type,
                        'quantity': str(quantity),
                    },
                )

                request.session['stripe_checkout_session_id'] = checkout_session.id

                return redirect(checkout_session.url, code=303)

            except stripe.error.StripeError as e:
                messages.error(request, f'Payment error: {str(e)}')
                return redirect('concerts:order_tickets', slug=slug)
    else:
        form = ConcertTicketOrderForm(concert=concert)

    context = {
        'concert': concert,
        'form': form,
    }
    return render(request, 'concerts/order_tickets.html', context)


def checkout_success(request, slug):
    """Handle successful Stripe checkout for concert tickets."""
    concert = get_object_or_404(Concert, slug=slug)
    session_id = request.GET.get('session_id')

    if not session_id:
        messages.error(request, 'Invalid payment session.')
        return redirect('concerts:detail', slug=slug)

    try:
        # Retrieve the checkout session from Stripe
        checkout_session = stripe.checkout.Session.retrieve(session_id)

        if checkout_session.payment_status != 'paid':
            messages.error(request, 'Payment was not completed.')
            return redirect('concerts:detail', slug=slug)

        # Get order data from session
        order_data = request.session.get('concert_order')
        if not order_data or order_data.get('concert_id') != concert.id:
            # Check if order already exists
            existing = ConcertTicketOrder.objects.filter(
                stripe_checkout_session_id=session_id
            ).first()
            if existing:
                messages.success(request, f'Your tickets for {concert.title} have been booked!')
                return redirect('concerts:detail', slug=slug)

            messages.error(request, 'Order data not found.')
            return redirect('concerts:detail', slug=slug)

        # Check for duplicate order
        existing_order = ConcertTicketOrder.objects.filter(
            stripe_checkout_session_id=session_id
        ).first()

        if existing_order:
            messages.success(request, f'Your tickets for {concert.title} have been booked!')
        else:
            # Create the order
            from decimal import Decimal
            order = ConcertTicketOrder.objects.create(
                concert=concert,
                email=order_data['email'],
                name=order_data['name'],
                phone=order_data.get('phone', ''),
                ticket_type=order_data['ticket_type'],
                quantity=order_data['quantity'],
                unit_price=Decimal(order_data['unit_price']),
                total_price=Decimal(order_data['total_price']),
                status='paid',
                paid_at=timezone.now(),
                stripe_checkout_session_id=session_id,
            )

            # Update tickets sold count
            concert.tickets_sold += order.quantity
            concert.save(update_fields=['tickets_sold'])

            # Send confirmation email
            send_ticket_confirmation_email(order)

            messages.success(
                request,
                f'Payment successful! Your {order.quantity} ticket(s) for {concert.title} '
                f'have been booked. A confirmation email has been sent to {order.email}.'
            )

        # Clear session data
        if 'concert_order' in request.session:
            del request.session['concert_order']
        if 'stripe_checkout_session_id' in request.session:
            del request.session['stripe_checkout_session_id']

        return redirect('concerts:detail', slug=slug)

    except stripe.error.StripeError as e:
        messages.error(request, f'Error verifying payment: {str(e)}')
        return redirect('concerts:detail', slug=slug)


def checkout_cancel(request, slug):
    """Handle cancelled Stripe checkout for concert tickets."""
    concert = get_object_or_404(Concert, slug=slug)

    # Clear session data
    if 'concert_order' in request.session:
        del request.session['concert_order']
    if 'stripe_checkout_session_id' in request.session:
        del request.session['stripe_checkout_session_id']

    messages.info(request, 'Payment was cancelled. Your order was not completed.')
    return redirect('concerts:order_tickets', slug=slug)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Handle Stripe webhooks for concert payment confirmation."""
    from core.stripe_utils import verify_webhook

    event, error_response = verify_webhook(request)
    if error_response:
        return error_response

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        metadata = session.get('metadata', {})
        concert_id = metadata.get('concert_id')

        if concert_id:
            # Find pending order and mark as paid
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


def send_ticket_confirmation_email(order):
    """Send ticket confirmation email."""
    concert = order.concert
    subject = f'Ticket Confirmation - {concert.title}'

    ticket_type_label = 'Full Price' if order.ticket_type == 'full' else concert.discount_label

    message = f"""
Hello {order.name},

Thank you for your ticket purchase!

BOOKING CONFIRMATION
--------------------
Order ID: #{order.id}

CONCERT DETAILS
---------------
{concert.title}

Date: {concert.date.strftime('%A, %d %B %Y')}
Time: {concert.time.strftime('%I:%M %p')}
{f"Doors open: {concert.doors_open.strftime('%I:%M %p')}" if concert.doors_open else ""}

Venue: {concert.venue_name}
{concert.venue_address}
{concert.venue_postcode}

TICKETS
-------
Type: {ticket_type_label}
Quantity: {order.quantity}
Total paid: £{order.total_price}

Please bring this email or show it on your phone at the door.

We look forward to seeing you!

Best regards,
Polyphonica Recorder Trio
"""

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [order.email],
            fail_silently=True,
        )
        order.confirmation_sent = True
        order.save(update_fields=['confirmation_sent'])
    except Exception:
        pass
