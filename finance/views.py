"""
Finance views for staff dashboard, expense management, and reporting.
"""
import csv
from datetime import date

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import HttpResponse

from .models import Expense, StripeTransaction, ExpenseCategory
from .services import FinanceService
from .forms import ExpenseForm, DateRangeForm
from workshops.models import Workshop
from concerts.models import Concert


@staff_member_required
def dashboard(request):
    """Finance dashboard with overview."""
    service = FinanceService()

    # Parse date range from request or use tax year default
    if request.GET.get('start_date') and request.GET.get('end_date'):
        form = DateRangeForm(request.GET)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
        else:
            start_date, end_date = service.get_uk_tax_year_dates()
    else:
        start_date, end_date = service.get_uk_tax_year_dates()
        form = DateRangeForm(initial={
            'start_date': start_date,
            'end_date': end_date,
        })

    # Get summary data
    summary = service.get_profit_summary(start_date, end_date)

    # Get unsynced count for warning
    unsynced = service.get_unsynced_payments_count()

    # Recent transactions
    recent_transactions = StripeTransaction.objects.filter(
        transaction_date__date__gte=start_date,
        transaction_date__date__lte=end_date
    ).select_related(
        'workshop_registration__workshop',
        'workshop_registration__user',
        'concert_order__concert'
    ).order_by('-transaction_date')[:10]

    # Recent expenses
    recent_expenses = Expense.objects.filter(
        expense_date__gte=start_date,
        expense_date__lte=end_date
    ).select_related('workshop', 'concert', 'created_by').order_by('-expense_date')[:10]

    context = {
        'form': form,
        'summary': summary,
        'unsynced': unsynced,
        'recent_transactions': recent_transactions,
        'recent_expenses': recent_expenses,
        'tax_year_label': service.get_tax_year_label(start_date),
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'finance/dashboard.html', context)


@staff_member_required
def expense_list(request):
    """List all expenses with filtering."""
    service = FinanceService()

    # Date range
    if request.GET.get('start_date') and request.GET.get('end_date'):
        form = DateRangeForm(request.GET)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
        else:
            start_date, end_date = service.get_uk_tax_year_dates()
    else:
        start_date, end_date = service.get_uk_tax_year_dates()
        form = DateRangeForm(initial={
            'start_date': start_date,
            'end_date': end_date,
        })

    expenses = Expense.objects.filter(
        expense_date__gte=start_date,
        expense_date__lte=end_date
    ).select_related('workshop', 'concert', 'created_by').order_by('-expense_date')

    # Category filter
    category = request.GET.get('category')
    if category:
        expenses = expenses.filter(category=category)

    # Calculate totals
    expense_summary = service.get_expense_summary(start_date, end_date)

    context = {
        'expenses': expenses,
        'form': form,
        'category_filter': category,
        'category_choices': ExpenseCategory.choices,
        'summary': expense_summary,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'finance/expense_list.html', context)


@staff_member_required
def expense_create(request):
    """Create a new expense."""
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.created_by = request.user
            expense.save()
            messages.success(request, 'Expense created successfully.')
            return redirect('finance:expense_list')
    else:
        form = ExpenseForm()

    context = {
        'form': form,
        'action': 'Create',
    }
    return render(request, 'finance/expense_form.html', context)


@staff_member_required
def expense_edit(request, pk):
    """Edit an expense."""
    expense = get_object_or_404(Expense, pk=pk)

    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense updated successfully.')
            return redirect('finance:expense_list')
    else:
        form = ExpenseForm(instance=expense)

    context = {
        'form': form,
        'expense': expense,
        'action': 'Edit',
    }
    return render(request, 'finance/expense_form.html', context)


@staff_member_required
def expense_delete(request, pk):
    """Delete an expense."""
    expense = get_object_or_404(Expense, pk=pk)

    if request.method == 'POST':
        # Delete receipt file if exists
        if expense.receipt:
            expense.receipt.delete()
        expense.delete()
        messages.success(request, 'Expense deleted.')
        return redirect('finance:expense_list')

    context = {
        'expense': expense,
    }
    return render(request, 'finance/expense_delete.html', context)


@staff_member_required
def workshop_financials(request, pk):
    """Detailed financials for a workshop."""
    service = FinanceService()
    data = service.get_workshop_financials(pk)

    context = {
        **data,
    }
    return render(request, 'finance/event_financials.html', context)


@staff_member_required
def concert_financials(request, pk):
    """Detailed financials for a concert."""
    service = FinanceService()
    data = service.get_concert_financials(pk)

    context = {
        **data,
    }
    return render(request, 'finance/event_financials.html', context)


@staff_member_required
def event_comparison(request):
    """Compare financials across events."""
    service = FinanceService()

    # Date range
    if request.GET.get('start_date') and request.GET.get('end_date'):
        form = DateRangeForm(request.GET)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
        else:
            start_date, end_date = service.get_uk_tax_year_dates()
    else:
        start_date, end_date = service.get_uk_tax_year_dates()
        form = DateRangeForm(initial={
            'start_date': start_date,
            'end_date': end_date,
        })

    # Get comparison data
    comparison = service.get_events_comparison(start_date, end_date)

    context = {
        'form': form,
        'workshops': comparison['workshops'],
        'concerts': comparison['concerts'],
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'finance/event_comparison.html', context)


@staff_member_required
def export_csv(request):
    """Export financial data as CSV for tax year."""
    service = FinanceService()

    # Get date range
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    if start_date_str and end_date_str:
        try:
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
        except ValueError:
            start_date, end_date = service.get_uk_tax_year_dates()
    else:
        start_date, end_date = service.get_uk_tax_year_dates()

    # Create response
    tax_year = service.get_tax_year_label(start_date)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="polyphonica-finance-{tax_year}.csv"'

    writer = csv.writer(response)

    # Header
    writer.writerow([f'Polyphonica Financial Report - Tax Year {tax_year}'])
    writer.writerow([f'Period: {start_date.strftime("%d %B %Y")} to {end_date.strftime("%d %B %Y")}'])
    writer.writerow([])

    # Income section
    writer.writerow(['INCOME'])
    writer.writerow(['Date', 'Type', 'Description', 'Gross (GBP)', 'Stripe Fee (GBP)', 'Net (GBP)'])

    transactions = StripeTransaction.objects.filter(
        transaction_date__date__gte=start_date,
        transaction_date__date__lte=end_date
    ).select_related(
        'workshop_registration__workshop',
        'workshop_registration__user',
        'concert_order__concert'
    ).order_by('transaction_date')

    income_gross = 0
    income_fees = 0
    income_net = 0

    for trans in transactions:
        if trans.workshop_registration:
            desc = f"Workshop: {trans.workshop_registration.workshop.title} ({trans.workshop_registration.user.get_full_name() or trans.workshop_registration.user.email})"
        else:
            desc = f"Concert: {trans.concert_order.concert.title} ({trans.concert_order.name})"

        writer.writerow([
            trans.transaction_date.strftime('%Y-%m-%d'),
            trans.get_transaction_type_display(),
            desc,
            f"{trans.gross_pounds:.2f}",
            f"{trans.fee_pounds:.2f}",
            f"{trans.net_pounds:.2f}",
        ])

        income_gross += trans.gross_pounds
        income_fees += trans.fee_pounds
        income_net += trans.net_pounds

    writer.writerow([])
    writer.writerow(['', '', 'INCOME TOTALS', f"{income_gross:.2f}", f"{income_fees:.2f}", f"{income_net:.2f}"])
    writer.writerow([])

    # Expenses section
    writer.writerow(['EXPENSES'])
    writer.writerow(['Date', 'Category', 'Description', 'Amount (GBP)', 'Linked Event', 'Notes'])

    expenses = Expense.objects.filter(
        expense_date__gte=start_date,
        expense_date__lte=end_date
    ).select_related('workshop', 'concert').order_by('expense_date')

    expense_total = 0

    for exp in expenses:
        linked = ''
        if exp.workshop:
            linked = f"Workshop: {exp.workshop.title}"
        elif exp.concert:
            linked = f"Concert: {exp.concert.title}"

        writer.writerow([
            exp.expense_date.strftime('%Y-%m-%d'),
            exp.get_category_display(),
            exp.description,
            f"{exp.amount:.2f}",
            linked,
            exp.notes or '',
        ])

        expense_total += exp.amount

    writer.writerow([])
    writer.writerow(['', '', 'EXPENSES TOTAL', f"{expense_total:.2f}"])
    writer.writerow([])

    # Summary section
    net_profit = income_net - float(expense_total)

    writer.writerow(['SUMMARY'])
    writer.writerow(['Description', 'Amount (GBP)'])
    writer.writerow(['Total Gross Income', f"{income_gross:.2f}"])
    writer.writerow(['Total Stripe Fees', f"{income_fees:.2f}"])
    writer.writerow(['Total Net Income', f"{income_net:.2f}"])
    writer.writerow(['Total Expenses', f"{expense_total:.2f}"])
    writer.writerow(['Net Profit/Loss', f"{net_profit:.2f}"])

    return response
