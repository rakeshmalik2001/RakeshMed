from __future__ import annotations

from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed


class ExpiringTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        ttl_seconds = int(getattr(settings, "AUTH_TOKEN_TTL_SECONDS", 0) or 0)

        if ttl_seconds > 0:
            age_seconds = (timezone.now() - token.created).total_seconds()
            if age_seconds >= ttl_seconds:
                token.delete()
                raise AuthenticationFailed("Session expired. Please login again.")

        if not getattr(user, "can_sign_in", False):
            token.delete()
            raise AuthenticationFailed("Account access is no longer allowed.")

        if getattr(user, "force_password_reset", False) or getattr(user, "password_expired", False):
            token.delete()
            raise AuthenticationFailed("Password reset required before continuing.")

        return user, token
