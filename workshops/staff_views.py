from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django import forms

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

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


@staff_member_required
def workshop_attendees_pdf(request, pk):
    """Generate PDF attendance list for a workshop."""
    workshop = get_object_or_404(Workshop, pk=pk)

    # Get paid/confirmed registrations only
    registrations = WorkshopRegistration.objects.filter(
        workshop=workshop,
        status__in=['paid', 'attended']
    ).select_related('user').order_by('user__last_name', 'user__first_name')

    # Create the HttpResponse object with PDF headers
    response = HttpResponse(content_type='application/pdf')
    filename = f"attendees-{workshop.slug}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # Create the PDF document (landscape orientation)
    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=15*mm,
        bottomMargin=15*mm
    )

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=2*mm
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=5*mm,
        textColor=colors.grey
    )

    # Build content
    elements = []

    # Title
    elements.append(Paragraph(workshop.title, title_style))

    # Workshop details
    workshop_date = workshop.date.strftime('%A, %d %B %Y')
    workshop_time = f"{workshop.start_time.strftime('%H:%M')} - {workshop.end_time.strftime('%H:%M')}"
    venue = workshop.venue_name if workshop.is_in_person else "Online"

    details = f"{workshop_date} | {workshop_time} | {venue}"
    elements.append(Paragraph(details, subtitle_style))

    elements.append(Spacer(1, 5*mm))

    # Attendance table
    if registrations:
        # Table header - landscape gives us more width for signature column
        if workshop.is_in_person:
            header = ['#', 'Name', 'Phone', 'Instruments', 'Signature']
            col_widths = [10*mm, 60*mm, 35*mm, 80*mm, 70*mm]
        else:
            header = ['#', 'Name', 'Email', 'Signature']
            col_widths = [10*mm, 70*mm, 80*mm, 95*mm]

        data = [header]

        # Table rows
        for i, reg in enumerate(registrations, 1):
            name = reg.user.get_full_name() or reg.user.username
            phone = reg.phone or '-'
            email = reg.user.email
            instruments = reg.instruments or '-'

            if workshop.is_in_person:
                row = [str(i), name, phone, instruments, '']
            else:
                row = [str(i), name, email, '']

            data.append(row)

        # Create table
        table = Table(data, colWidths=col_widths, repeatRows=1)

        # Table styling
        table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4*mm),
            ('TOPPADDING', (0, 0), (-1, 0), 4*mm),

            # Body
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 3*mm),
            ('TOPPADDING', (0, 1), (-1, -1), 3*mm),

            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),

            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),

            # Alignment
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),  # Number column
            ('ALIGN', (-1, 0), (-1, -1), 'CENTER'),  # Present column
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        elements.append(table)

        # Summary
        elements.append(Spacer(1, 8*mm))
        summary = f"Total confirmed attendees: {registrations.count()} / {workshop.max_participants}"
        elements.append(Paragraph(summary, styles['Normal']))

    else:
        elements.append(Paragraph("No confirmed registrations.", styles['Normal']))

    # Build PDF
    doc.build(elements)

    return response


class EmailAttendeesForm(forms.Form):
    """Form for composing email to workshop attendees."""
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'placeholder': 'Email subject'})
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 10, 'placeholder': 'Your message to attendees...'})
    )


@staff_member_required
def workshop_email_attendees(request, pk):
    """Send email to all confirmed attendees of a workshop."""
    workshop = get_object_or_404(Workshop, pk=pk)

    # Get confirmed registrations
    registrations = WorkshopRegistration.objects.filter(
        workshop=workshop,
        status__in=['paid', 'attended']
    ).select_related('user')

    recipient_count = registrations.count()

    if request.method == 'POST':
        form = EmailAttendeesForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']

            # Send emails with HTML formatting
            sent_count = 0
            errors = []
            for reg in registrations:
                if reg.user.email:
                    # Render HTML email
                    html_message = render_to_string('emails/admin_message.html', {
                        'subject': subject,
                        'message': message,
                        'user': reg.user,
                        'workshop': workshop,
                    })

                    try:
                        send_mail(
                            subject,
                            message,
                            settings.DEFAULT_FROM_EMAIL,
                            [reg.user.email],
                            html_message=html_message,
                            fail_silently=False,
                        )
                        sent_count += 1
                    except Exception as e:
                        errors.append(f'{reg.user.email}: {str(e)}')

            if sent_count > 0:
                messages.success(request, f'Email sent successfully to {sent_count} attendee(s).')
                if errors:
                    messages.error(request, f'Failed to send to: {", ".join(errors)}')
                return redirect('workshops:staff_workshop_attendees', pk=workshop.pk)
            elif errors:
                messages.error(request, f'Failed to send emails: {", ".join(errors)}')
            else:
                messages.warning(request, 'No attendees with email addresses found.')
    else:
        # Pre-fill subject with workshop name
        initial_subject = f"Reminder: {workshop.title} - {workshop.date.strftime('%A, %d %B')}"
        form = EmailAttendeesForm(initial={'subject': initial_subject})

    context = {
        'form': form,
        'workshop': workshop,
        'recipient_count': recipient_count,
        'registrations': registrations,
    }
    return render(request, 'workshops/staff/workshop_email.html', context)
