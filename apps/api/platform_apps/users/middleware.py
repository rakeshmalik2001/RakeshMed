from django.contrib import auth, messages
from django.shortcuts import redirect


class AccountStatusMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/api/"):
            return self.get_response(request)
        user = getattr(request, "user", None)
        reset_paths = (
            "/password-reset/",
            "/reset/",
            "/logout/",
        )
        if getattr(user, "is_authenticated", False) and not user.can_sign_in:
            auth.logout(request)
            messages.error(request, "Your account can no longer access the portal.")
            return redirect("login")
        if (
            getattr(user, "is_authenticated", False)
            and not request.path.startswith(reset_paths)
            and (getattr(user, "force_password_reset", False) or getattr(user, "password_expired", False))
        ):
            auth.logout(request)
            messages.warning(request, "Password reset is required before you can continue.")
            return redirect("password_reset")
        return self.get_response(request)
