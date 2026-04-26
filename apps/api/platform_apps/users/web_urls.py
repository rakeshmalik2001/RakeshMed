from django.urls import path

from .web_views import (
    LoginView,
    LogoutView,
    MFAChallengeView,
    PortalPasswordResetCompleteView,
    PortalPasswordResetConfirmView,
    PortalPasswordResetDoneView,
    PortalPasswordResetView,
    RegistrationView,
)


urlpatterns = [
    path("register/", RegistrationView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("mfa-challenge/", MFAChallengeView.as_view(), name="mfa_challenge"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("password-reset/", PortalPasswordResetView.as_view(), name="password_reset"),
    path("password-reset/done/", PortalPasswordResetDoneView.as_view(), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", PortalPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("reset/done/", PortalPasswordResetCompleteView.as_view(), name="password_reset_complete"),
]
