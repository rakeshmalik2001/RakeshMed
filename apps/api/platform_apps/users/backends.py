from django.contrib.auth.backends import ModelBackend

from .access import ACCOUNT_STATUS_ACTIVE
from .models import User


class EmailOrPhoneBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = kwargs.get("email") or username or kwargs.get(User.USERNAME_FIELD)
        if not identifier or not password:
            return None

        user = (
            User.objects.filter(email__iexact=identifier).first()
            or User.objects.filter(phone_number=identifier).first()
        )
        if not user or not user.check_password(password):
            return None
        if not self.user_can_authenticate(user):
            return None
        if getattr(user, "account_status", ACCOUNT_STATUS_ACTIVE) != ACCOUNT_STATUS_ACTIVE:
            return None
        if getattr(user, "approval_status", "approved") != "approved":
            return None
        return user
