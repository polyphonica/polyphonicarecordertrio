"""
Email utility functions for sending transactional emails.
"""
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


def send_email(
    subject,
    recipient,
    plain_message,
    html_template=None,
    html_context=None,
    fail_silently=True,
):
    """
    Send an email with optional HTML template.

    Args:
        subject: Email subject line
        recipient: Email address to send to
        plain_message: Plain text version of the email
        html_template: Optional path to HTML email template
        html_context: Optional context dict for HTML template
        fail_silently: Whether to suppress exceptions (default True)

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    html_message = None
    if html_template and html_context:
        try:
            html_message = render_to_string(html_template, html_context)
        except Exception:
            # Fall back to plain text if template fails
            html_message = None

    try:
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            html_message=html_message,
            fail_silently=fail_silently,
        )
        return True
    except Exception:
        return False
