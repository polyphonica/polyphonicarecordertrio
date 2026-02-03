import logging

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


class EmailOrUsernameBackend(ModelBackend):
    """
    Authentication backend that allows login with email or username.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        user = None

        # Try to find user by email first
        try:
            user = User.objects.get(email__iexact=username)
        except User.MultipleObjectsReturned:
            logger.error(
                f"Multiple users found with email: {username}. "
                "Run 'python manage.py find_duplicate_users' to fix."
            )
            return None
        except User.DoesNotExist:
            # Try username
            try:
                user = User.objects.get(username__iexact=username)
            except User.MultipleObjectsReturned:
                logger.error(
                    f"Multiple users found with username: {username}. "
                    "Run 'python manage.py find_duplicate_users' to fix."
                )
                return None
            except User.DoesNotExist:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
