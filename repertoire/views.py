import json
from io import BytesIO

from django.db import models
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django import forms

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from .models import Composer, Piece, Movement, Programme, ProgrammeItem


# =============================================================================
# Forms
# =============================================================================

class ComposerForm(forms.ModelForm):
    class Meta:
        model = Composer
        fields = ['name', 'birth_year', 'death_year', 'nationality', 'bio']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-primary-300 rounded-lg focus:ring-2 focus:ring-accent-500'}),
            'birth_year': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-primary-300 rounded-lg focus:ring-2 focus:ring-accent-500', 'placeholder': 'e.g., 1685'}),
            'death_year': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-primary-300 rounded-lg focus:ring-2 focus:ring-accent-500', 'placeholder': 'e.g., 1750'}),
            'nationality': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-primary-300 rounded-lg focus:ring-2 focus:ring-accent-500', 'placeholder': 'e.g., German'}),
            'bio': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-primary-300 rounded-lg focus:ring-2 focus:ring-accent-500', 'rows': 4}),
        }


class PieceForm(forms.ModelForm):
    class Meta:
        model = Piece
        fields = ['title', 'composer', 'duration', 'catalogue_number', 'instrumentation', 'notes']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-primary-300 rounded-lg focus:ring-2 focus:ring-accent-500'}),
            'composer': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-primary-300 rounded-lg focus:ring-2 focus:ring-accent-500'}),
            'duration': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-primary-300 rounded-lg focus:ring-2 focus:ring-accent-500', 'placeholder': 'Minutes'}),
            'catalogue_number': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-primary-300 rounded-lg focus:ring-2 focus:ring-accent-500', 'placeholder': 'e.g., BWV 1079'}),
            'instrumentation': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-primary-300 rounded-lg focus:ring-2 focus:ring-accent-500'}),
            'notes': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-primary-300 rounded-lg focus:ring-2 focus:ring-accent-500', 'rows': 4}),
        }


class ProgrammeForm(forms.ModelForm):
    class Meta:
        model = Programme
        fields = ['title', 'status', 'notes']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-primary-300 rounded-lg focus:ring-2 focus:ring-accent-500'}),
            'status': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-primary-300 rounded-lg focus:ring-2 focus:ring-accent-500'}),
            'notes': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-primary-300 rounded-lg focus:ring-2 focus:ring-accent-500', 'rows': 3}),
        }


class ProgrammeItemForm(forms.ModelForm):
    class Meta:
        model = ProgrammeItem
        fields = ['item_type', 'piece', 'title', 'custom_duration', 'talk_text', 'notes']
        widgets = {
            'item_type': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-primary-300 rounded-lg'}),
            'piece': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-primary-300 rounded-lg'}),
            'title': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-primary-300 rounded-lg', 'placeholder': 'e.g., Introduction, Interval'}),
            'custom_duration': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-primary-300 rounded-lg', 'placeholder': 'Minutes'}),
            'talk_text': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-primary-300 rounded-lg', 'rows': 4}),
            'notes': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-primary-300 rounded-lg', 'rows': 2}),
        }


# =============================================================================
# Composer Views
# =============================================================================

@staff_member_required
def composer_list(request):
    composers = Composer.objects.all()
    return render(request, 'repertoire/composer_list.html', {'composers': composers})


@staff_member_required
def composer_add(request):
    if request.method == 'POST':
        form = ComposerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Composer added successfully.')
            return redirect('repertoire:composer_list')
    else:
        form = ComposerForm()
    return render(request, 'repertoire/composer_form.html', {'form': form, 'action': 'Add'})


@staff_member_required
def composer_edit(request, pk):
    composer = get_object_or_404(Composer, pk=pk)
    if request.method == 'POST':
        form = ComposerForm(request.POST, instance=composer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Composer updated successfully.')
            return redirect('repertoire:composer_list')
    else:
        form = ComposerForm(instance=composer)
    return render(request, 'repertoire/composer_form.html', {'form': form, 'action': 'Edit', 'composer': composer})


@staff_member_required
def composer_delete(request, pk):
    composer = get_object_or_404(Composer, pk=pk)
    if request.method == 'POST':
        composer.delete()
        messages.success(request, 'Composer deleted successfully.')
        return redirect('repertoire:composer_list')
    return render(request, 'repertoire/composer_delete.html', {'composer': composer})


# =============================================================================
# Piece Views
# =============================================================================

@staff_member_required
def piece_list(request):
    pieces = Piece.objects.select_related('composer').prefetch_related('movements').all()
    return render(request, 'repertoire/piece_list.html', {'pieces': pieces})


@staff_member_required
def piece_add(request):
    if request.method == 'POST':
        form = PieceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Piece added successfully.')
            return redirect('repertoire:piece_list')
    else:
        form = PieceForm()
    return render(request, 'repertoire/piece_form.html', {'form': form, 'action': 'Add'})


@staff_member_required
def piece_edit(request, pk):
    piece = get_object_or_404(Piece, pk=pk)
    if request.method == 'POST':
        form = PieceForm(request.POST, instance=piece)
        if form.is_valid():
            form.save()
            messages.success(request, 'Piece updated successfully.')
            return redirect('repertoire:piece_list')
    else:
        form = PieceForm(instance=piece)
    return render(request, 'repertoire/piece_form.html', {'form': form, 'action': 'Edit', 'piece': piece})


@staff_member_required
def piece_delete(request, pk):
    piece = get_object_or_404(Piece, pk=pk)
    if request.method == 'POST':
        piece.delete()
        messages.success(request, 'Piece deleted successfully.')
        return redirect('repertoire:piece_list')
    return render(request, 'repertoire/piece_delete.html', {'piece': piece})


# =============================================================================
# Movement Views
# =============================================================================

@staff_member_required
@require_POST
def movement_add(request, pk):
    """Add a movement to a piece."""
    piece = get_object_or_404(Piece, pk=pk)
    name = request.POST.get('name', '').strip()

    if name:
        # Get next order
        max_order = piece.movements.aggregate(max_order=models.Max('order'))['max_order'] or 0
        movement = Movement.objects.create(
            piece=piece,
            name=name,
            order=max_order + 1
        )
        return JsonResponse({
            'success': True,
            'movement': {
                'id': movement.id,
                'name': movement.name,
            }
        })

    return JsonResponse({'success': False, 'error': 'Name is required'})


@staff_member_required
@require_POST
def movement_delete(request, pk):
    """Delete a movement."""
    movement = get_object_or_404(Movement, pk=pk)
    movement.delete()
    return JsonResponse({'success': True})


# =============================================================================
# Programme Views
# =============================================================================

@staff_member_required
def programme_list(request):
    programmes = Programme.objects.all()
    return render(request, 'repertoire/programme_list.html', {'programmes': programmes})


@staff_member_required
def programme_add(request):
    if request.method == 'POST':
        form = ProgrammeForm(request.POST)
        if form.is_valid():
            programme = form.save()
            messages.success(request, 'Programme created successfully.')
            return redirect('repertoire:programme_detail', pk=programme.pk)
    else:
        form = ProgrammeForm()
    return render(request, 'repertoire/programme_form.html', {'form': form, 'action': 'Create'})


@staff_member_required
def programme_detail(request, pk):
    """Programme builder view with drag-drop interface."""
    programme = get_object_or_404(Programme, pk=pk)
    items = programme.items.select_related('piece', 'piece__composer').prefetch_related('piece__movements').all()
    pieces = Piece.objects.select_related('composer').all()

    return render(request, 'repertoire/programme_detail.html', {
        'programme': programme,
        'items': items,
        'pieces': pieces,
    })


@staff_member_required
def programme_edit(request, pk):
    programme = get_object_or_404(Programme, pk=pk)
    if request.method == 'POST':
        form = ProgrammeForm(request.POST, instance=programme)
        if form.is_valid():
            form.save()
            messages.success(request, 'Programme updated successfully.')
            return redirect('repertoire:programme_detail', pk=programme.pk)
    else:
        form = ProgrammeForm(instance=programme)
    return render(request, 'repertoire/programme_form.html', {'form': form, 'action': 'Edit', 'programme': programme})


@staff_member_required
def programme_delete(request, pk):
    programme = get_object_or_404(Programme, pk=pk)
    if request.method == 'POST':
        programme.delete()
        messages.success(request, 'Programme deleted successfully.')
        return redirect('repertoire:programme_list')
    return render(request, 'repertoire/programme_delete.html', {'programme': programme})


# =============================================================================
# Programme Item AJAX Views
# =============================================================================

@staff_member_required
@require_POST
def programme_add_item(request, pk):
    """Add an item to a programme."""
    programme = get_object_or_404(Programme, pk=pk)

    item_type = request.POST.get('item_type')
    piece_id = request.POST.get('piece_id')
    title = request.POST.get('title', '')
    speaker = request.POST.get('speaker', '')
    duration = request.POST.get('duration')
    talk_text = request.POST.get('talk_text', '')

    # Get the next order position
    max_order = programme.items.aggregate(max_order=models.Max('order'))['max_order'] or 0

    item = ProgrammeItem(
        programme=programme,
        item_type=item_type,
        order=max_order + 1,
    )

    if item_type == 'piece' and piece_id:
        item.piece_id = piece_id
    else:
        item.title = title
        item.speaker = speaker
        item.custom_duration = int(duration) if duration else None
        item.talk_text = talk_text

    item.save()

    return JsonResponse({
        'success': True,
        'item': {
            'id': item.id,
            'type': item.item_type,
            'title': str(item),
            'duration': item.duration_display,
        }
    })


@staff_member_required
@require_POST
def programme_reorder(request, pk):
    """Reorder programme items."""
    programme = get_object_or_404(Programme, pk=pk)

    try:
        data = json.loads(request.body)
        item_ids = data.get('items', [])

        for index, item_id in enumerate(item_ids):
            ProgrammeItem.objects.filter(pk=item_id, programme=programme).update(order=index)

        # Recalculate total duration
        programme.refresh_from_db()

        return JsonResponse({
            'success': True,
            'total_duration': programme.total_duration_display
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@staff_member_required
def programme_item_edit(request, pk):
    """Edit a programme item."""
    item = get_object_or_404(ProgrammeItem, pk=pk)

    if request.method == 'POST':
        if item.item_type == 'piece':
            piece_id = request.POST.get('piece_id')
            if piece_id:
                item.piece_id = piece_id
        else:
            item.title = request.POST.get('title', '')
            item.speaker = request.POST.get('speaker', '')
            duration = request.POST.get('duration')
            item.custom_duration = int(duration) if duration else None
            item.talk_text = request.POST.get('talk_text', '')

        item.notes = request.POST.get('notes', '')
        item.save()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'item': {
                    'id': item.id,
                    'title': str(item),
                    'duration': item.duration_display,
                }
            })

        messages.success(request, 'Item updated successfully.')
        return redirect('repertoire:programme_detail', pk=item.programme.pk)

    pieces = Piece.objects.select_related('composer').all() if item.item_type == 'piece' else None
    return render(request, 'repertoire/programme_item_edit.html', {
        'item': item,
        'pieces': pieces,
    })


@staff_member_required
@require_POST
def programme_item_delete(request, pk):
    """Delete a programme item."""
    item = get_object_or_404(ProgrammeItem, pk=pk)
    programme = item.programme
    item.delete()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'total_duration': programme.total_duration_display
        })

    messages.success(request, 'Item removed from programme.')
    return redirect('repertoire:programme_detail', pk=programme.pk)


# =============================================================================
# API Views
# =============================================================================

@staff_member_required
@require_GET
def piece_search_api(request):
    """Search pieces for autocomplete."""
    query = request.GET.get('q', '')
    pieces = Piece.objects.select_related('composer').filter(
        models.Q(title__icontains=query) |
        models.Q(composer__name__icontains=query) |
        models.Q(catalogue_number__icontains=query)
    )[:20]

    return JsonResponse({
        'pieces': [
            {
                'id': p.id,
                'title': p.title,
                'composer': p.composer.name,
                'duration': p.duration,
                'duration_display': p.duration_display,
                'catalogue_number': p.catalogue_number,
            }
            for p in pieces
        ]
    })


# =============================================================================
# PDF Generation
# =============================================================================

@staff_member_required
def programme_pdf_performer(request, pk):
    """Generate performer version PDF with all timings and talk texts."""
    programme = get_object_or_404(Programme, pk=pk)
    items = programme.items.select_related('piece', 'piece__composer').all()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=10*mm,
        alignment=1,  # Center
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        alignment=1,
        spaceAfter=10*mm,
    )
    item_style = ParagraphStyle(
        'Item',
        parent=styles['Normal'],
        fontSize=11,
    )
    talk_style = ParagraphStyle(
        'Talk',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.darkgrey,
        leftIndent=10*mm,
        spaceBefore=2*mm,
        spaceAfter=4*mm,
    )

    elements = []

    # Title
    elements.append(Paragraph(f"PERFORMER'S PROGRAMME", title_style))
    elements.append(Paragraph(programme.title, styles['Heading2']))
    elements.append(Paragraph(f"Total duration: {programme.total_duration_display}", subtitle_style))
    elements.append(Spacer(1, 5*mm))

    # Build table data
    table_data = [['#', 'Item', 'Duration', 'Running Time']]
    running_time = 0

    for i, item in enumerate(items, 1):
        duration = item.duration or 0

        if item.item_type == 'piece' and item.piece:
            title = f"{item.piece.title}"
            if item.piece.catalogue_number:
                title += f" ({item.piece.catalogue_number})"
            title += f"\n{item.piece.composer.name}"
            # Add movements if any
            if item.piece.movements.exists():
                movements = [m.name for m in item.piece.movements.all()]
                title += "\n" + ", ".join(movements)
        elif item.item_type == 'interval':
            title = "— INTERVAL —"
        else:
            title = item.title or "Talk"
            if item.speaker:
                title += f"\n{item.speaker}"

        running_time += duration
        running_mins = running_time

        table_data.append([
            str(i),
            title,
            item.duration_display,
            f"{running_mins}m"
        ])

    # Create table
    table = Table(table_data, colWidths=[10*mm, 100*mm, 25*mm, 30*mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.25, 0.22, 0.19)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (3, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(table)

    # Add talk texts
    talks = [item for item in items if item.item_type == 'talk' and item.talk_text]
    if talks:
        elements.append(Spacer(1, 10*mm))
        elements.append(Paragraph("TALK NOTES", styles['Heading2']))
        for item in talks:
            talk_header = item.title or 'Talk'
            if item.speaker:
                talk_header += f" — {item.speaker}"
            elements.append(Paragraph(f"<b>{talk_header}</b>", item_style))
            elements.append(Paragraph(item.talk_text, talk_style))

    doc.build(elements)

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{programme.title} - Performer.pdf"'
    return response


@staff_member_required
def programme_pdf_public(request, pk):
    """Generate public version PDF - standard concert programme format."""
    programme = get_object_or_404(Programme, pk=pk)
    items = programme.items.select_related('piece', 'piece__composer').all()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=25*mm, bottomMargin=25*mm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=20,
        spaceAfter=15*mm,
        alignment=1,
    )
    composer_style = ParagraphStyle(
        'Composer',
        parent=styles['Normal'],
        fontSize=12,
        fontName='Helvetica-Bold',
        spaceBefore=8*mm,
    )
    piece_style = ParagraphStyle(
        'Piece',
        parent=styles['Normal'],
        fontSize=11,
        leftIndent=5*mm,
        spaceBefore=2*mm,
    )
    interval_style = ParagraphStyle(
        'Interval',
        parent=styles['Normal'],
        fontSize=11,
        alignment=1,
        spaceBefore=10*mm,
        spaceAfter=10*mm,
        textColor=colors.grey,
    )

    elements = []

    # Title
    elements.append(Paragraph(programme.title, title_style))
    elements.append(Spacer(1, 5*mm))

    # Group items by composer for nice display, but maintain order
    current_composer = None

    for item in items:
        if item.item_type == 'interval':
            elements.append(Paragraph("— Interval —", interval_style))
            current_composer = None
        elif item.item_type == 'piece' and item.piece:
            composer = item.piece.composer
            if composer != current_composer:
                composer_text = composer.name
                if composer.dates_display:
                    composer_text += f" {composer.dates_display}"
                elements.append(Paragraph(composer_text, composer_style))
                current_composer = composer

            piece_text = item.piece.title
            if item.piece.catalogue_number:
                piece_text += f", {item.piece.catalogue_number}"
            elements.append(Paragraph(piece_text, piece_style))

            # Add movements if any
            if item.piece.movements.exists():
                for movement in item.piece.movements.all():
                    elements.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;{movement.name}", ParagraphStyle(
                        'Movement',
                        parent=styles['Normal'],
                        fontSize=10,
                        leftIndent=10*mm,
                        textColor=colors.grey,
                    )))
        # Talks are not shown in public programme

    # Add performer info at bottom
    elements.append(Spacer(1, 15*mm))
    elements.append(Paragraph("Polyphonica Recorder Trio", ParagraphStyle(
        'Performer',
        parent=styles['Normal'],
        fontSize=12,
        alignment=1,
        fontName='Helvetica-Oblique',
    )))

    doc.build(elements)

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{programme.title} - Programme.pdf"'
    return response
