"""
Migration to add unique constraint on User.email field.

IMPORTANT: Before running this migration, you must clean up any existing
duplicate emails in the database. Run:

    python manage.py find_duplicate_users --fix

This migration adds a unique constraint to the auth_user.email column
to prevent multiple users from having the same email address.
Only enforced for non-empty emails (allows multiple users with blank email).
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '__first__'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunSQL(
            # Partial unique index - only enforced when email is not empty
            sql="CREATE UNIQUE INDEX auth_user_email_unique ON auth_user (email) WHERE email != '';",
            reverse_sql='DROP INDEX IF EXISTS auth_user_email_unique;',
        ),
    ]
