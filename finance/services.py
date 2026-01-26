"""
Finance service providing centralized calculation logic for all financial reporting.
"""
from datetime import date
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple

from django.db.models import Sum, Count, Q
from django.utils import timezone

from .models import StripeTransaction, Expense


class FinanceService:
    """
    Centralized service for financial calculations and reporting.
    """

    @staticmethod
    def get_uk_tax_year_dates(year: Optional[int] = None) -> Tuple[date, date]:
        """
        Get start and end dates for UK tax year.
        UK tax year runs 6 April to 5 April.

        Args:
            year: The tax year starting year (e.g., 2024 for 2024-25).
                  If None, returns current tax year.

        Returns:
            Tuple of (start_date, end_date)
        """
        today = timezone.now().date()

        if year is None:
            # Determine current tax year
            if today.month < 4 or (today.month == 4 and today.day < 6):
                year = today.year - 1
            else:
                year = today.year

        start_date = date(year, 4, 6)
        end_date = date(year + 1, 4, 5)

        return start_date, end_date

    @staticmethod
    def get_tax_year_label(start_date: date) -> str:
        """Return human-readable tax year label e.g., '2024-25'."""
        return f"{start_date.year}-{str(start_date.year + 1)[-2:]}"

    def get_income_summary(
        self,
        start_date: date,
        end_date: date,
        workshop_id: Optional[int] = None,
        concert_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calculate income summary for a date range.

        Returns dict with:
        - workshop_gross: Total workshop income (gross)
        - workshop_fees: Total Stripe fees for workshops
        - workshop_net: Net workshop income
        - workshop_count: Number of paid workshop registrations
        - concert_gross: Total concert ticket income (gross)
        - concert_fees: Total Stripe fees for concerts
        - concert_net: Net concert income
        - concert_count: Number of paid concert orders
        - total_gross: Combined gross income
        - total_fees: Combined Stripe fees
        - total_net: Combined net income
        """
        # Workshop income
        workshop_filters = Q(
            workshop_registration__isnull=False,
            transaction_date__date__gte=start_date,
            transaction_date__date__lte=end_date
        )
        if workshop_id:
            workshop_filters &= Q(workshop_registration__workshop_id=workshop_id)

        workshop_totals = StripeTransaction.objects.filter(
            workshop_filters
        ).aggregate(
            gross=Sum('gross_amount'),
            fees=Sum('stripe_fee'),
            net=Sum('net_amount'),
            count=Count('id')
        )

        # Concert income
        concert_filters = Q(
            concert_order__isnull=False,
            transaction_date__date__gte=start_date,
            transaction_date__date__lte=end_date
        )
        if concert_id:
            concert_filters &= Q(concert_order__concert_id=concert_id)

        concert_totals = StripeTransaction.objects.filter(
            concert_filters
        ).aggregate(
            gross=Sum('gross_amount'),
            fees=Sum('stripe_fee'),
            net=Sum('net_amount'),
            count=Count('id')
        )

        # Convert pence to pounds (handle None values)
        def to_pounds(pence):
            return Decimal(pence or 0) / 100

        workshop_gross = to_pounds(workshop_totals['gross'])
        workshop_fees = to_pounds(workshop_totals['fees'])
        workshop_net = to_pounds(workshop_totals['net'])

        concert_gross = to_pounds(concert_totals['gross'])
        concert_fees = to_pounds(concert_totals['fees'])
        concert_net = to_pounds(concert_totals['net'])

        return {
            'workshop_gross': workshop_gross,
            'workshop_fees': workshop_fees,
            'workshop_net': workshop_net,
            'workshop_count': workshop_totals['count'] or 0,
            'concert_gross': concert_gross,
            'concert_fees': concert_fees,
            'concert_net': concert_net,
            'concert_count': concert_totals['count'] or 0,
            'total_gross': workshop_gross + concert_gross,
            'total_fees': workshop_fees + concert_fees,
            'total_net': workshop_net + concert_net,
        }

    def get_expense_summary(
        self,
        start_date: date,
        end_date: date,
        workshop_id: Optional[int] = None,
        concert_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calculate expense summary for a date range.

        Returns dict with:
        - by_category: Dict of category -> total
        - workshop_total: Expenses linked to workshops
        - concert_total: Expenses linked to concerts
        - general_total: Unlinked expenses
        - total: Total expenses
        """
        filters = Q(
            expense_date__gte=start_date,
            expense_date__lte=end_date
        )
        if workshop_id:
            filters &= Q(workshop_id=workshop_id)
        elif concert_id:
            filters &= Q(concert_id=concert_id)

        expenses = Expense.objects.filter(filters)

        # By category
        by_category = {}
        for category, label in Expense.category.field.choices:
            total = expenses.filter(category=category).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0')
            by_category[category] = {
                'label': label,
                'total': total,
            }

        # By event type
        workshop_total = expenses.filter(
            workshop__isnull=False
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        concert_total = expenses.filter(
            concert__isnull=False
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        general_total = expenses.filter(
            workshop__isnull=True,
            concert__isnull=True
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        total = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0')

        return {
            'by_category': by_category,
            'workshop_total': workshop_total,
            'concert_total': concert_total,
            'general_total': general_total,
            'total': total,
        }

    def get_profit_summary(
        self,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Calculate overall profit/loss for a date range.
        """
        income = self.get_income_summary(start_date, end_date)
        expenses = self.get_expense_summary(start_date, end_date)

        net_profit = income['total_net'] - expenses['total']

        return {
            'income': income,
            'expenses': expenses,
            'net_profit': net_profit,
            'start_date': start_date,
            'end_date': end_date,
        }

    def get_workshop_financials(self, workshop_id: int) -> Dict[str, Any]:
        """
        Get detailed financials for a specific workshop.
        """
        from workshops.models import Workshop

        workshop = Workshop.objects.get(id=workshop_id)

        transactions = StripeTransaction.objects.filter(
            workshop_registration__workshop_id=workshop_id
        ).select_related('workshop_registration__user')

        expenses = Expense.objects.filter(
            workshop_id=workshop_id
        ).select_related('created_by')

        # Income totals
        income_totals = transactions.aggregate(
            gross=Sum('gross_amount'),
            fees=Sum('stripe_fee'),
            net=Sum('net_amount'),
            count=Count('id')
        )

        gross = Decimal(income_totals['gross'] or 0) / 100
        fees = Decimal(income_totals['fees'] or 0) / 100
        net = Decimal(income_totals['net'] or 0) / 100

        # Expense totals by category
        expense_by_category = {}
        for category, label in Expense.category.field.choices:
            total = expenses.filter(category=category).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0')
            if total > 0:
                expense_by_category[category] = {
                    'label': label,
                    'total': total,
                }

        expense_total = expenses.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        return {
            'event': workshop,
            'event_type': 'workshop',
            'transactions': transactions,
            'transaction_count': income_totals['count'] or 0,
            'gross_income': gross,
            'stripe_fees': fees,
            'net_income': net,
            'expenses': expenses,
            'expense_by_category': expense_by_category,
            'expense_total': expense_total,
            'profit': net - expense_total,
        }

    def get_concert_financials(self, concert_id: int) -> Dict[str, Any]:
        """
        Get detailed financials for a specific concert.
        """
        from concerts.models import Concert

        concert = Concert.objects.get(id=concert_id)

        transactions = StripeTransaction.objects.filter(
            concert_order__concert_id=concert_id
        ).select_related('concert_order')

        expenses = Expense.objects.filter(
            concert_id=concert_id
        ).select_related('created_by')

        # Income totals
        income_totals = transactions.aggregate(
            gross=Sum('gross_amount'),
            fees=Sum('stripe_fee'),
            net=Sum('net_amount'),
            count=Count('id')
        )

        gross = Decimal(income_totals['gross'] or 0) / 100
        fees = Decimal(income_totals['fees'] or 0) / 100
        net = Decimal(income_totals['net'] or 0) / 100

        # Expense totals by category
        expense_by_category = {}
        for category, label in Expense.category.field.choices:
            total = expenses.filter(category=category).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0')
            if total > 0:
                expense_by_category[category] = {
                    'label': label,
                    'total': total,
                }

        expense_total = expenses.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        return {
            'event': concert,
            'event_type': 'concert',
            'transactions': transactions,
            'transaction_count': income_totals['count'] or 0,
            'gross_income': gross,
            'stripe_fees': fees,
            'net_income': net,
            'expenses': expenses,
            'expense_by_category': expense_by_category,
            'expense_total': expense_total,
            'profit': net - expense_total,
        }

    def get_events_comparison(
        self,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Get financials for all events in date range for comparison.
        """
        from workshops.models import Workshop
        from concerts.models import Concert

        # Get workshops with their financials
        workshops = Workshop.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).order_by('-date')

        workshop_data = []
        for workshop in workshops:
            data = self.get_workshop_financials(workshop.id)
            workshop_data.append(data)

        # Get concerts with internal ticket sales
        concerts = Concert.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            ticket_source='internal'
        ).order_by('-date')

        concert_data = []
        for concert in concerts:
            data = self.get_concert_financials(concert.id)
            concert_data.append(data)

        return {
            'workshops': workshop_data,
            'concerts': concert_data,
            'start_date': start_date,
            'end_date': end_date,
        }

    def get_unsynced_payments_count(self) -> Dict[str, int]:
        """
        Get count of payments that haven't been synced with Stripe fees yet.
        """
        from workshops.models import WorkshopRegistration
        from concerts.models import ConcertTicketOrder

        workshop_unsynced = WorkshopRegistration.objects.filter(
            status='paid',
            stripe_payment_intent_id__startswith='pi_'
        ).exclude(
            stripe_transaction__isnull=False
        ).count()

        concert_unsynced = ConcertTicketOrder.objects.filter(
            status='paid',
            stripe_payment_intent_id__startswith='pi_'
        ).exclude(
            stripe_transaction__isnull=False
        ).count()

        return {
            'workshop': workshop_unsynced,
            'concert': concert_unsynced,
            'total': workshop_unsynced + concert_unsynced,
        }
