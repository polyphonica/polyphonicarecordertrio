"""
Management command to import legacy workshop bookings from CSV.

Usage:
    python manage.py import_legacy_bookings data.csv --workshop=1 --dry-run
    python manage.py import_legacy_bookings data.csv --workshop="workshop-slug"
    python manage.py import_legacy_bookings data.csv --workshop=1

Expected CSV columns (Stripe export names in parentheses):
    Required:
        - email (or "Customer Email")
        - name (or "Card Name")
        - amount (or "Amount") - gross amount in pounds, e.g. 45.00
        - fee (or "Fee") - Stripe fee in pounds, e.g. 1.35
        - payment_intent_id (or "PaymentIntent ID") - e.g. pi_xxx
        - date (or "Created date (UTC)") - e.g. 2024-01-15

    Optional:
        - phone (or "Customer Phone")
        - charge_id (or "ID") - e.g. ch_xxx
        - balance_transaction_id - e.g. txn_xxx
"""
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from workshops.models import Workshop, WorkshopRegistration
from finance.models import StripeTransaction


class Command(BaseCommand):
    help = 'Import legacy workshop bookings from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            help='Path to the CSV file containing booking data'
        )
        parser.add_argument(
            '--workshop',
            required=True,
            help='Workshop ID (number) or slug to link bookings to'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be imported without making changes'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        workshop_ref = options['workshop']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY RUN MODE - No changes will be made]\n'))

        # Get the workshop
        workshop = self.get_workshop(workshop_ref)
        self.stdout.write(f"Workshop: {workshop.title} ({workshop.date})")
        self.stdout.write(f"Current registrations: {workshop.current_registrations}")
        self.stdout.write(f"Legacy bookings count: {workshop.legacy_bookings}\n")

        # Read and validate CSV
        try:
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except FileNotFoundError:
            raise CommandError(f"CSV file not found: {csv_file}")
        except Exception as e:
            raise CommandError(f"Error reading CSV file: {e}")

        if not rows:
            raise CommandError("CSV file is empty")

        self.stdout.write(f"Found {len(rows)} rows in CSV\n")

        # Validate all rows first
        validated_rows = []
        errors = []

        for i, row in enumerate(rows, start=1):
            try:
                validated = self.validate_row(row, i)
                validated_rows.append(validated)
            except ValueError as e:
                errors.append(f"Row {i}: {e}")

        if errors:
            self.stdout.write(self.style.ERROR("Validation errors found:"))
            for error in errors:
                self.stdout.write(self.style.ERROR(f"  {error}"))
            raise CommandError("Please fix the CSV errors and try again")

        # Check for duplicate emails in CSV
        emails = [r['email'] for r in validated_rows]
        duplicates = set([e for e in emails if emails.count(e) > 1])
        if duplicates:
            self.stdout.write(self.style.ERROR(f"Duplicate emails in CSV: {', '.join(duplicates)}"))
            raise CommandError("Each customer should only appear once in the CSV")

        # Check for existing registrations
        existing_emails = []
        for row in validated_rows:
            if User.objects.filter(email=row['email']).exists():
                user = User.objects.get(email=row['email'])
                if WorkshopRegistration.objects.filter(workshop=workshop, user=user).exists():
                    existing_emails.append(row['email'])

        if existing_emails:
            self.stdout.write(self.style.WARNING(
                f"\nWarning: {len(existing_emails)} users already registered for this workshop:"
            ))
            for email in existing_emails:
                self.stdout.write(f"  - {email}")
            self.stdout.write("")

        # Show preview
        self.stdout.write(self.style.SUCCESS("Data to import:"))
        self.stdout.write("-" * 80)

        for row in validated_rows:
            status = "SKIP (already registered)" if row['email'] in existing_emails else "NEW"
            self.stdout.write(
                f"  {row['name']:30} {row['email']:35} "
                f"£{row['amount']:>7.2f} (fee: £{row['fee']:.2f}) [{status}]"
            )

        self.stdout.write("-" * 80)

        new_count = len(validated_rows) - len(existing_emails)
        self.stdout.write(f"\nTotal: {len(validated_rows)} rows")
        self.stdout.write(f"New registrations to create: {new_count}")
        self.stdout.write(f"Skipping (already registered): {len(existing_emails)}\n")

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "[DRY RUN] No changes made. Remove --dry-run to import."
            ))
            return

        if new_count == 0:
            self.stdout.write(self.style.SUCCESS("Nothing to import - all users already registered."))
            return

        # Import the data
        created_users = 0
        created_registrations = 0
        created_transactions = 0

        with transaction.atomic():
            for row in validated_rows:
                if row['email'] in existing_emails:
                    continue

                # Get or create user
                user, user_created = self.get_or_create_user(row)
                if user_created:
                    created_users += 1
                    self.stdout.write(f"Created user: {user.email}")

                # Create registration
                registration = WorkshopRegistration.objects.create(
                    workshop=workshop,
                    user=user,
                    status='paid',
                    phone=row.get('phone', ''),
                    amount_paid=row['amount'],
                    stripe_payment_intent_id=row['payment_intent_id'],
                    paid_at=row['transaction_date'],
                    terms_accepted=True,
                    terms_accepted_at=row['transaction_date'],
                    confirmation_sent=True,  # Mark as sent since these are legacy
                )
                created_registrations += 1
                self.stdout.write(f"Created registration: {user.email} -> {workshop.title}")

                # Create Stripe transaction record
                gross_pence = int(row['amount'] * 100)
                fee_pence = int(row['fee'] * 100)
                net_pence = gross_pence - fee_pence

                StripeTransaction.objects.create(
                    transaction_type='workshop',
                    workshop_registration=registration,
                    payment_intent_id=row['payment_intent_id'],
                    charge_id=row.get('charge_id', ''),
                    balance_transaction_id=row.get('balance_transaction_id', ''),
                    gross_amount=gross_pence,
                    stripe_fee=fee_pence,
                    net_amount=net_pence,
                    transaction_date=row['transaction_date'],
                )
                created_transactions += 1

            # Update the legacy_bookings count (reduce it since we've imported them)
            if workshop.legacy_bookings >= created_registrations:
                workshop.legacy_bookings -= created_registrations
                workshop.save(update_fields=['legacy_bookings'])
                self.stdout.write(f"\nUpdated workshop legacy_bookings: {workshop.legacy_bookings}")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Import complete!\n"
            f"  Users created: {created_users}\n"
            f"  Registrations created: {created_registrations}\n"
            f"  Stripe transactions created: {created_transactions}"
        ))

    def get_workshop(self, workshop_ref):
        """Get workshop by ID or slug."""
        try:
            workshop_id = int(workshop_ref)
            try:
                return Workshop.objects.get(id=workshop_id)
            except Workshop.DoesNotExist:
                raise CommandError(f"Workshop with ID {workshop_id} not found")
        except ValueError:
            # Not an integer, try as slug
            try:
                return Workshop.objects.get(slug=workshop_ref)
            except Workshop.DoesNotExist:
                raise CommandError(f"Workshop with slug '{workshop_ref}' not found")

    def validate_row(self, row, row_num):
        """Validate a CSV row and return normalized data."""
        # Normalize column names (lowercase, strip whitespace)
        row = {k.lower().strip(): v.strip() for k, v in row.items()}

        # Email (required) - Stripe uses "customer email"
        email = (
            row.get('email', '') or
            row.get('customer email', '')
        )
        if not email:
            raise ValueError("Missing email")
        email = email.lower()

        # Name (required) - Stripe uses "card name"
        name = (
            row.get('name', '') or
            row.get('card name', '') or
            row.get('customer name', '')
        )
        if name:
            parts = name.split(' ', 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ''
        elif 'first_name' in row:
            first_name = row.get('first_name', '')
            last_name = row.get('last_name', '')
            name = f"{first_name} {last_name}".strip()
        else:
            raise ValueError("Missing name (need 'Card Name', 'name', or 'first_name'/'last_name' column)")

        if not name:
            raise ValueError("Name is empty")

        # Amount (required - gross amount in pounds)
        amount_str = row.get('amount', '') or row.get('gross_amount', '') or row.get('gross', '')
        if not amount_str:
            raise ValueError("Missing amount")
        try:
            # Remove currency symbols and commas
            amount_str = amount_str.replace('£', '').replace(',', '').strip()
            amount = Decimal(amount_str)
        except InvalidOperation:
            raise ValueError(f"Invalid amount: {amount_str}")

        # Fee (required - Stripe fee in pounds)
        fee_str = row.get('fee', '') or row.get('stripe_fee', '')
        if not fee_str:
            raise ValueError("Missing fee")
        try:
            fee_str = fee_str.replace('£', '').replace(',', '').strip()
            fee = Decimal(fee_str)
        except InvalidOperation:
            raise ValueError(f"Invalid fee: {fee_str}")

        # Payment Intent ID (required) - Stripe uses "paymentintent id"
        payment_intent_id = (
            row.get('payment_intent_id', '') or
            row.get('paymentintent id', '') or
            row.get('payment_intent', '')
        )
        if not payment_intent_id:
            raise ValueError("Missing payment_intent_id")
        if not payment_intent_id.startswith('pi_'):
            raise ValueError(f"Invalid payment_intent_id (should start with 'pi_'): {payment_intent_id}")

        # Transaction date (required) - Stripe uses "created date (utc)"
        date_str = (
            row.get('date', '') or
            row.get('created date (utc)', '') or
            row.get('created (utc)', '') or
            row.get('transaction_date', '') or
            row.get('created', '')
        )
        if not date_str:
            raise ValueError("Missing date")
        transaction_date = self.parse_date(date_str)
        if not transaction_date:
            raise ValueError(f"Could not parse date: {date_str}")

        # Optional fields
        phone = row.get('phone', '') or row.get('customer phone', '')
        # Stripe uses "id" for charge_id
        charge_id = row.get('charge_id', '') or row.get('id', '')
        balance_transaction_id = row.get('balance_transaction_id', '') or row.get('balance_txn', '')

        return {
            'email': email,
            'name': name,
            'first_name': first_name,
            'last_name': last_name,
            'amount': amount,
            'fee': fee,
            'payment_intent_id': payment_intent_id,
            'transaction_date': transaction_date,
            'phone': phone,
            'charge_id': charge_id,
            'balance_transaction_id': balance_transaction_id,
        }

    def parse_date(self, date_str):
        """Parse various date formats."""
        formats = [
            '%Y-%m-%d',           # 2024-01-15
            '%Y-%m-%d %H:%M:%S',  # 2024-01-15 10:30:00
            '%d/%m/%Y',           # 15/01/2024
            '%d/%m/%Y %H:%M',     # 15/01/2024 10:30
            '%d-%m-%Y',           # 15-01-2024
            '%m/%d/%Y',           # 01/15/2024 (US format)
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return timezone.make_aware(dt)
            except ValueError:
                continue

        return None

    def get_or_create_user(self, row):
        """Get existing user or create new one."""
        email = row['email']

        try:
            user = User.objects.get(email=email)
            return user, False
        except User.DoesNotExist:
            pass

        # Create username from email
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        # Create user with unusable password (they'll need to reset)
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=row['first_name'],
            last_name=row['last_name'],
        )
        user.set_unusable_password()
        user.save()

        return user, True
