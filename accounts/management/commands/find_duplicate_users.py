from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Count, F


class Command(BaseCommand):
    help = 'Find and optionally merge users with duplicate email addresses'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Automatically merge duplicate users (keeps most recently active)',
        )

    def handle(self, *args, **options):
        # Find duplicate emails (excluding blank emails)
        duplicates = (
            User.objects.exclude(email='')
            .values('email')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
            .order_by('-count')
        )

        if not duplicates:
            self.stdout.write(self.style.SUCCESS('No duplicate emails found.'))
            return

        self.stdout.write(
            self.style.WARNING(f'Found {len(duplicates)} email(s) with duplicates:')
        )
        self.stdout.write('')

        for dup in duplicates:
            email = dup['email']
            # Sort by last_login desc (nulls last), then date_joined desc
            users = User.objects.filter(email=email).order_by(
                F('last_login').desc(nulls_last=True),
                '-date_joined'
            )

            self.stdout.write(f"Email: {email}")
            self.stdout.write("-" * 50)

            for i, user in enumerate(users):
                marker = " (KEEP)" if i == 0 and options['fix'] else ""
                self.stdout.write(
                    f"  ID: {user.id}, Username: {user.username}, "
                    f"Joined: {user.date_joined.strftime('%Y-%m-%d')}, "
                    f"Last login: {user.last_login.strftime('%Y-%m-%d') if user.last_login else 'Never'}"
                    f"{marker}"
                )

            self.stdout.write('')

            if options['fix']:
                self.merge_users(users)

        if not options['fix']:
            self.stdout.write('')
            self.stdout.write(
                self.style.NOTICE(
                    'Run with --fix to automatically merge duplicates '
                    '(keeps most recently active user).'
                )
            )

    def merge_users(self, users):
        """Merge duplicate users, keeping the first one (most recently active)."""
        primary_user = users[0]
        duplicates_to_delete = users[1:]

        for dup_user in duplicates_to_delete:
            # Transfer workshop registrations
            from workshops.models import WorkshopRegistration
            registrations = WorkshopRegistration.objects.filter(user=dup_user)
            transferred = registrations.update(user=primary_user)
            if transferred:
                self.stdout.write(
                    f"  Transferred {transferred} workshop registration(s) "
                    f"from {dup_user.username} to {primary_user.username}"
                )

            # Transfer concert purchases
            from concerts.models import ConcertPurchase
            purchases = ConcertPurchase.objects.filter(user=dup_user)
            transferred = purchases.update(user=primary_user)
            if transferred:
                self.stdout.write(
                    f"  Transferred {transferred} concert purchase(s) "
                    f"from {dup_user.username} to {primary_user.username}"
                )

            # Delete the duplicate user
            username = dup_user.username
            dup_user.delete()
            self.stdout.write(
                self.style.SUCCESS(f"  Deleted duplicate user: {username}")
            )

        self.stdout.write('')
