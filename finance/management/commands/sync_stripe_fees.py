"""
Management command to sync Stripe fees from Balance Transactions API.

Usage:
    python manage.py sync_stripe_fees              # Sync last 30 days
    python manage.py sync_stripe_fees --days=7     # Sync last 7 days
    python manage.py sync_stripe_fees --all        # Sync all historical data
    python manage.py sync_stripe_fees --dry-run    # Preview without saving
"""
import stripe
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone

from finance.models import StripeTransaction
from workshops.models import WorkshopRegistration
from concerts.models import ConcertTicketOrder


class Command(BaseCommand):
    help = 'Sync Stripe fees from balance transactions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to look back (default: 30)'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Process all transactions, not just recent ones'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without making changes'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-sync even if fees already exist (updates existing records)'
        )

    def handle(self, *args, **options):
        stripe.api_key = settings.STRIPE_SECRET_KEY

        if not stripe.api_key:
            raise CommandError('STRIPE_SECRET_KEY not configured')

        days = options['days']
        dry_run = options['dry_run']
        process_all = options['all']
        force = options['force']

        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY RUN MODE]'))

        self.stdout.write(f"Syncing Stripe fees...")

        # Build lookup of payment intents to process
        all_intents = {}

        # Workshop registrations
        workshop_query = WorkshopRegistration.objects.filter(
            status='paid',
            stripe_payment_intent_id__startswith='pi_'
        )
        if not process_all:
            cutoff_date = timezone.now() - timedelta(days=days)
            workshop_query = workshop_query.filter(paid_at__gte=cutoff_date)

        if not force:
            workshop_query = workshop_query.exclude(stripe_transaction__isnull=False)

        for reg in workshop_query:
            all_intents[reg.stripe_payment_intent_id] = ('workshop', reg)

        self.stdout.write(f"Found {len([k for k, v in all_intents.items() if v[0] == 'workshop'])} workshop payments to sync")

        # Concert ticket orders
        concert_query = ConcertTicketOrder.objects.filter(
            status='paid',
            stripe_payment_intent_id__startswith='pi_'
        )
        if not process_all:
            cutoff_date = timezone.now() - timedelta(days=days)
            concert_query = concert_query.filter(paid_at__gte=cutoff_date)

        if not force:
            concert_query = concert_query.exclude(stripe_transaction__isnull=False)

        for order in concert_query:
            all_intents[order.stripe_payment_intent_id] = ('concert', order)

        concert_count = len([k for k, v in all_intents.items() if v[0] == 'concert'])
        self.stdout.write(f"Found {concert_count} concert payments to sync")

        total_count = len(all_intents)
        self.stdout.write(f"Total: {total_count} payments to process")

        if not all_intents:
            self.stdout.write(self.style.SUCCESS('No new transactions to sync'))
            return

        created_count = 0
        updated_count = 0
        error_count = 0
        skipped_count = 0

        for payment_intent_id, (trans_type, record) in all_intents.items():
            try:
                # Get the payment intent to find the charge
                pi = stripe.PaymentIntent.retrieve(payment_intent_id)

                if not pi.latest_charge:
                    self.stdout.write(
                        self.style.WARNING(
                            f"No charge found for {payment_intent_id[:25]}..."
                        )
                    )
                    skipped_count += 1
                    continue

                # Get the charge to find the balance transaction
                charge = stripe.Charge.retrieve(pi.latest_charge)

                if not charge.balance_transaction:
                    self.stdout.write(
                        self.style.WARNING(
                            f"No balance transaction for charge {charge.id[:20]}..."
                        )
                    )
                    skipped_count += 1
                    continue

                # Get the balance transaction for fee details
                bt = stripe.BalanceTransaction.retrieve(charge.balance_transaction)

                if dry_run:
                    self.stdout.write(
                        f"[DRY RUN] {trans_type}: gross=£{bt.amount/100:.2f} "
                        f"fee=£{bt.fee/100:.2f} net=£{bt.net/100:.2f}"
                    )
                    continue

                # Check if transaction already exists
                existing = None
                if trans_type == 'workshop':
                    existing = StripeTransaction.objects.filter(
                        workshop_registration=record
                    ).first()
                else:
                    existing = StripeTransaction.objects.filter(
                        concert_order=record
                    ).first()

                if existing and force:
                    # Update existing record
                    existing.charge_id = charge.id
                    existing.balance_transaction_id = bt.id
                    existing.gross_amount = bt.amount
                    existing.stripe_fee = bt.fee
                    existing.net_amount = bt.net
                    existing.transaction_date = timezone.make_aware(
                        datetime.fromtimestamp(bt.created)
                    )
                    existing.save()
                    updated_count += 1
                    self.stdout.write(
                        f"Updated: {trans_type} fee=£{bt.fee/100:.2f}"
                    )
                elif not existing:
                    # Create new transaction record
                    transaction_data = {
                        'transaction_type': trans_type,
                        'payment_intent_id': payment_intent_id,
                        'charge_id': charge.id,
                        'balance_transaction_id': bt.id,
                        'gross_amount': bt.amount,
                        'stripe_fee': bt.fee,
                        'net_amount': bt.net,
                        'transaction_date': timezone.make_aware(
                            datetime.fromtimestamp(bt.created)
                        ),
                    }

                    if trans_type == 'workshop':
                        transaction_data['workshop_registration'] = record
                    else:
                        transaction_data['concert_order'] = record

                    StripeTransaction.objects.create(**transaction_data)
                    created_count += 1

                    self.stdout.write(
                        f"Created: {trans_type} fee=£{bt.fee/100:.2f}"
                    )

            except stripe.error.StripeError as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"Stripe error for {payment_intent_id[:25]}...: {e}"
                    )
                )
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"Error processing {payment_intent_id[:25]}...: {e}"
                    )
                )

        # Summary
        self.stdout.write('')
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"[DRY RUN] Would process {total_count} transactions"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Sync complete: {created_count} created, {updated_count} updated, "
                    f"{skipped_count} skipped, {error_count} errors"
                )
            )
