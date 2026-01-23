"""
Stripe utility functions for payment processing.
"""
import json
import stripe
from django.conf import settings
from django.http import HttpResponse


def verify_webhook(request):
    """
    Verify and parse a Stripe webhook request.

    Returns:
        tuple: (event_dict, error_response)
        - If successful: (event_dict, None)
        - If failed: (None, HttpResponse with error status)
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    if settings.STRIPE_WEBHOOK_SECRET:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
            return event, None
        except ValueError:
            return None, HttpResponse(status=400)
        except stripe.error.SignatureVerificationError:
            return None, HttpResponse(status=400)
    else:
        # For testing without webhook secret
        try:
            event = json.loads(payload)
            return event, None
        except json.JSONDecodeError:
            return None, HttpResponse(status=400)


def create_checkout_session(
    product_name,
    description,
    unit_amount_pence,
    quantity,
    success_url,
    cancel_url,
    customer_email,
    metadata=None,
    payment_intent_metadata=None,
    payment_description=None,
):
    """
    Create a Stripe checkout session.

    Args:
        product_name: Name of the product/ticket
        description: Product description
        unit_amount_pence: Price per unit in pence (GBP)
        quantity: Number of items
        success_url: URL to redirect after successful payment
        cancel_url: URL to redirect after cancelled payment
        customer_email: Customer's email address
        metadata: Optional dict of metadata for the session
        payment_intent_metadata: Optional dict of metadata for the payment intent
        payment_description: Optional description for the payment intent

    Returns:
        stripe.checkout.Session object

    Raises:
        stripe.error.StripeError: If Stripe API call fails
    """
    session_params = {
        'payment_method_types': ['card'],
        'line_items': [{
            'price_data': {
                'currency': 'gbp',
                'unit_amount': unit_amount_pence,
                'product_data': {
                    'name': product_name,
                    'description': description,
                },
            },
            'quantity': quantity,
        }],
        'mode': 'payment',
        'success_url': success_url,
        'cancel_url': cancel_url,
        'customer_email': customer_email,
    }

    if metadata:
        session_params['metadata'] = metadata

    if payment_intent_metadata or payment_description:
        session_params['payment_intent_data'] = {}
        if payment_description:
            session_params['payment_intent_data']['description'] = payment_description
        if payment_intent_metadata:
            session_params['payment_intent_data']['metadata'] = payment_intent_metadata

    return stripe.checkout.Session.create(**session_params)
