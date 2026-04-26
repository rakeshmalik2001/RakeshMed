from __future__ import annotations

import csv
import json
import secrets
from urllib.parse import urlencode

from django.contrib import messages
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordResetCompleteView, PasswordResetConfirmView, PasswordResetDoneView, PasswordResetView
from django.core.mail import send_mail
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from platform_apps.audit.services import record_audit_event
from platform_apps.catalog.models import Brand, Category, Product, ProductSubstitute
from platform_apps.delivery.models import DeliveryShipment
from platform_apps.delivery.services import delivery_metrics_snapshot
from platform_apps.inventory.models import InventoryItem, LowStockRule, StockMovement
from platform_apps.notifications.models import Notification
from platform_apps.orders.models import Order, PaymentAttempt, RefundRequest, SettlementBatch
from platform_apps.prescriptions.models import Prescription

from .access import DASHBOARD_CONTENT, RoleRequiredMixin, resolve_dashboard_url
from .forms import LoginForm, MFAVerifyForm, RegistrationForm, SecurePortalPasswordSetForm, UniqueEmailPasswordResetForm, UserManagementForm
from .location_catalog import get_country_states_map
from .models import CustomerAddress, CustomerWebsiteActivityDaily, RolePermissionMatrix, SavedPaymentMethod, User, UserSavedFilterView, format_active_duration
from .role_catalog import get_role_catalog_payload
from .services import notify_admins_of_pending_approval, notify_user_of_approval_decision, send_user_password_reset_link


PORTAL_MFA_SESSION_USER_ID = "portal_mfa_user_id"
PORTAL_MFA_SESSION_CODE = "portal_mfa_code"
PORTAL_MFA_SESSION_EXPIRES_AT = "portal_mfa_expires_at"
PORTAL_MFA_SESSION_IDENTIFIER = "portal_mfa_identifier"
PORTAL_MFA_SESSION_RESEND_AFTER = "portal_mfa_resend_after"
PORTAL_MFA_SESSION_FAILED_ATTEMPTS = "portal_mfa_failed_attempts"
PORTAL_MFA_SESSION_BACKEND = "portal_mfa_backend"
PORTAL_MFA_TTL_SECONDS = int(getattr(settings, "PORTAL_MFA_TTL_SECONDS", 300))
PORTAL_MFA_RESEND_COOLDOWN_SECONDS = int(getattr(settings, "PORTAL_MFA_RESEND_COOLDOWN_SECONDS", 30))


def _require_password_reset_for_portal_user(request: HttpRequest, user: User, *, reason: str) -> HttpResponse:
    try:
        send_user_password_reset_link(user, request=request, initiated_by=user)
    except ValueError:
        messages.error(
            request,
            "Password reset is required before you can continue, but no reset email address is available. Contact support.",
        )
    else:
        record_audit_event(
            actor=user,
            event_type="portal_password_reset_required",
            entity_type="user",
            entity_id=user.pk,
            severity="warning",
            message=f"Portal sign-in blocked pending password reset for {user.email or user.phone_number}.",
            meta={"reason": reason},
        )
        messages.warning(
            request,
            "Password reset is required before you can continue. We sent a secure reset link to your email address.",
        )
    return redirect("login")


def _portal_request_ip(request: HttpRequest) -> str:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _generate_mfa_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _clear_portal_mfa_session(request: HttpRequest) -> None:
    for key in (
        PORTAL_MFA_SESSION_USER_ID,
        PORTAL_MFA_SESSION_CODE,
        PORTAL_MFA_SESSION_EXPIRES_AT,
        PORTAL_MFA_SESSION_IDENTIFIER,
        PORTAL_MFA_SESSION_RESEND_AFTER,
        PORTAL_MFA_SESSION_FAILED_ATTEMPTS,
        PORTAL_MFA_SESSION_BACKEND,
    ):
        request.session.pop(key, None)


def _send_portal_mfa_code(*, user: User, code: str) -> None:
    recipient = (user.email or "").strip()
    if not recipient:
        raise ValueError("MFA requires an email-enabled user account.")
    send_mail(
        subject="Your RakeshMed verification code",
        message=(
            f"Hello {user.full_name or user.email or user.phone_number},\n\n"
            f"Your portal verification code is: {code}\n\n"
            f"This code expires in {PORTAL_MFA_TTL_SECONDS // 60} minutes."
        ),
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@rakeshmed.local"),
        recipient_list=[recipient],
        fail_silently=False,
    )


def _start_portal_mfa_challenge(request: HttpRequest, user: User) -> None:
    code = _generate_mfa_code()
    now = timezone.now()
    request.session[PORTAL_MFA_SESSION_USER_ID] = user.pk
    request.session[PORTAL_MFA_SESSION_CODE] = code
    request.session[PORTAL_MFA_SESSION_EXPIRES_AT] = (now + timezone.timedelta(seconds=PORTAL_MFA_TTL_SECONDS)).isoformat()
    request.session[PORTAL_MFA_SESSION_IDENTIFIER] = user.email or user.phone_number
    request.session[PORTAL_MFA_SESSION_RESEND_AFTER] = (
        now + timezone.timedelta(seconds=PORTAL_MFA_RESEND_COOLDOWN_SECONDS)
    ).isoformat()
    request.session[PORTAL_MFA_SESSION_FAILED_ATTEMPTS] = 0
    request.session[PORTAL_MFA_SESSION_BACKEND] = getattr(user, "backend", settings.AUTHENTICATION_BACKENDS[0])
    request.session.modified = True
    _send_portal_mfa_code(user=user, code=code)


def _pending_portal_mfa_user(request: HttpRequest) -> User | None:
    user_id = request.session.get(PORTAL_MFA_SESSION_USER_ID)
    if not user_id:
        return None
    return User.objects.filter(pk=user_id).first()


def _mask_identifier(value: str) -> str:
    if "@" in value:
        name, domain = value.split("@", 1)
        if len(name) <= 2:
            masked_name = name[0] + "*" * max(len(name) - 1, 1)
        else:
            masked_name = name[:2] + "*" * max(len(name) - 2, 1)
        return f"{masked_name}@{domain}"
    if len(value) <= 4:
        return "*" * len(value)
    return "*" * (len(value) - 4) + value[-4:]


def access_denied_view(request, exception=None):
    return render(
        request,
        "errors/access_denied.html",
        {"dashboard_url": resolve_dashboard_url(request.user) if request.user.is_authenticated else reverse_lazy("login")},
        status=403,
    )


class RegistrationView(View):
    template_name = "registration/register.html"
    form_class = RegistrationForm

    def get_template_context(self, *, form):
        return {
            "form": form,
            "frontend_customer_register_url": getattr(settings, "FRONTEND_CUSTOMER_REGISTER_URL", "http://localhost:3000/signup"),
            "frontend_customer_account_url": getattr(settings, "FRONTEND_CUSTOMER_ACCOUNT_URL", "http://localhost:3000/account"),
        }

    def get(self, request):
        return render(request, self.template_name, self.get_template_context(form=self.form_class()))

    def post(self, request):
        form = self.form_class(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            record_audit_event(
                actor=user,
                event_type="auth_registered",
                entity_type="user",
                entity_id=user.pk,
                message=f"Portal registration completed for {user.email}.",
                meta={"role": user.role, "approval_status": user.approval_status},
            )
            if user.approval_status == "pending":
                notify_admins_of_pending_approval(user)
                messages.success(request, "Registration submitted. An administrator must approve your account before login.")
            else:
                messages.success(request, "Registration successful. Please sign in.")
            return redirect("login")
        return render(request, self.template_name, self.get_template_context(form=form))


class LoginView(View):
    template_name = "registration/login.html"
    form_class = LoginForm

    def get_template_context(self, *, form):
        return {
            "form": form,
            "frontend_customer_register_url": getattr(settings, "FRONTEND_CUSTOMER_REGISTER_URL", "http://localhost:3000/signup"),
            "frontend_customer_account_url": getattr(settings, "FRONTEND_CUSTOMER_ACCOUNT_URL", "http://localhost:3000/account"),
        }

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(resolve_dashboard_url(request.user))
        return render(request, self.template_name, self.get_template_context(form=self.form_class(request=request)))

    def post(self, request):
        form = self.form_class(request=request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.force_password_reset:
                return _require_password_reset_for_portal_user(request, user, reason="forced_reset")
            if user.password_expired:
                return _require_password_reset_for_portal_user(request, user, reason="password_expired")
            if user.mfa_enabled:
                try:
                    _start_portal_mfa_challenge(request, user)
                except ValueError as exc:
                    form.add_error(None, str(exc))
                    return render(request, self.template_name, self.get_template_context(form=form), status=400)
                record_audit_event(
                    actor=user,
                    event_type="portal_mfa_challenge_sent",
                    entity_type="user",
                    entity_id=user.pk,
                    message=f"Portal MFA challenge sent for {user.email or user.phone_number}.",
                    meta={"role": user.role},
                )
                messages.info(request, "We sent a 6-digit verification code to your email. Enter it to finish signing in.")
                return redirect("mfa_challenge")
            login(request, user)
            user.last_login = timezone.now()
            user.last_login_ip = _portal_request_ip(request)
            user.failed_login_attempts = 0
            user.account_locked = False
            user.updated_by = user
            user.save(update_fields=["last_login", "last_login_ip", "failed_login_attempts", "account_locked", "updated_by", "updated_at"])
            record_audit_event(
                actor=user,
                event_type="portal_login_success",
                entity_type="user",
                entity_id=user.pk,
                message=f"Portal login successful for {user.email}.",
                meta={"role": user.role},
            )
            messages.success(request, f"Welcome back, {user.full_name or user.email}.")
            return redirect(resolve_dashboard_url(user))

        email = (request.POST.get("email") or "").strip().lower()
        matched_user = User.objects.filter(email__iexact=email).first()
        record_audit_event(
            actor=matched_user,
            actor_label=email or "anonymous",
            event_type="portal_login_failed",
            entity_type="user",
            entity_id=matched_user.pk if matched_user else "",
            message=f"Portal login failed for {email or 'unknown email'}.",
            severity="warning",
            meta={"errors": form.errors.get_json_data()},
        )
        return render(request, self.template_name, self.get_template_context(form=form), status=400)


class MFAChallengeView(View):
    template_name = "registration/mfa_challenge.html"
    form_class = MFAVerifyForm
    max_attempts = 5

    def _context(self, request: HttpRequest, *, form: MFAVerifyForm) -> dict:
        pending_user = _pending_portal_mfa_user(request)
        resend_after = request.session.get(PORTAL_MFA_SESSION_RESEND_AFTER)
        resend_ready = True
        if resend_after:
            try:
                resend_ready = timezone.now() >= timezone.datetime.fromisoformat(resend_after)
            except ValueError:
                resend_ready = True
        return {
            "form": form,
            "pending_user": pending_user,
            "masked_identifier": _mask_identifier(request.session.get(PORTAL_MFA_SESSION_IDENTIFIER, "")),
            "resend_ready": resend_ready,
        }

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(resolve_dashboard_url(request.user))
        if not _pending_portal_mfa_user(request):
            messages.info(request, "Please sign in first to begin verification.")
            return redirect("login")
        return render(request, self.template_name, self._context(request, form=self.form_class()))

    def post(self, request):
        pending_user = _pending_portal_mfa_user(request)
        if not pending_user:
            messages.info(request, "Your verification session has expired. Please sign in again.")
            return redirect("login")

        action = (request.POST.get("action") or "verify").strip()
        if action == "resend":
            resend_after = request.session.get(PORTAL_MFA_SESSION_RESEND_AFTER)
            if resend_after:
                try:
                    if timezone.now() < timezone.datetime.fromisoformat(resend_after):
                        messages.warning(request, "Please wait a moment before requesting another code.")
                        return render(request, self.template_name, self._context(request, form=self.form_class()))
                except ValueError:
                    pass
            _start_portal_mfa_challenge(request, pending_user)
            record_audit_event(
                actor=pending_user,
                event_type="portal_mfa_code_resent",
                entity_type="user",
                entity_id=pending_user.pk,
                message=f"Portal MFA code resent for {pending_user.email or pending_user.phone_number}.",
            )
            messages.success(request, "A new verification code was sent.")
            return redirect("mfa_challenge")

        form = self.form_class(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, self._context(request, form=form), status=400)

        expires_at_raw = request.session.get(PORTAL_MFA_SESSION_EXPIRES_AT)
        stored_code = request.session.get(PORTAL_MFA_SESSION_CODE)
        expires_at = None
        if expires_at_raw:
            try:
                expires_at = timezone.datetime.fromisoformat(expires_at_raw)
            except ValueError:
                expires_at = None
        if not stored_code or not expires_at or timezone.now() > expires_at:
            _clear_portal_mfa_session(request)
            messages.error(request, "Your verification code expired. Please sign in again.")
            return redirect("login")

        failed_attempts = int(request.session.get(PORTAL_MFA_SESSION_FAILED_ATTEMPTS, 0))
        if form.cleaned_data["code"] != stored_code:
            failed_attempts += 1
            request.session[PORTAL_MFA_SESSION_FAILED_ATTEMPTS] = failed_attempts
            record_audit_event(
                actor=pending_user,
                event_type="portal_mfa_failed",
                entity_type="user",
                entity_id=pending_user.pk,
                severity="warning",
                message=f"Portal MFA verification failed for {pending_user.email or pending_user.phone_number}.",
                meta={"attempts": failed_attempts},
            )
            if failed_attempts >= self.max_attempts:
                _clear_portal_mfa_session(request)
                messages.error(request, "Too many invalid verification attempts. Please sign in again.")
                return redirect("login")
            form.add_error("code", "Verification code is incorrect.")
            return render(request, self.template_name, self._context(request, form=form), status=400)

        backend_path = request.session.get(PORTAL_MFA_SESSION_BACKEND, settings.AUTHENTICATION_BACKENDS[0])
        _clear_portal_mfa_session(request)
        if pending_user.force_password_reset:
            return _require_password_reset_for_portal_user(request, pending_user, reason="forced_reset")
        if pending_user.password_expired:
            return _require_password_reset_for_portal_user(request, pending_user, reason="password_expired")
        login(request, pending_user, backend=backend_path)
        pending_user.last_login = timezone.now()
        pending_user.last_login_ip = _portal_request_ip(request)
        pending_user.failed_login_attempts = 0
        pending_user.account_locked = False
        pending_user.updated_by = pending_user
        pending_user.save(update_fields=["last_login", "last_login_ip", "failed_login_attempts", "account_locked", "updated_by", "updated_at"])
        record_audit_event(
            actor=pending_user,
            event_type="portal_mfa_verified",
            entity_type="user",
            entity_id=pending_user.pk,
            message=f"Portal MFA verified for {pending_user.email or pending_user.phone_number}.",
            meta={"role": pending_user.role},
        )
        messages.success(request, f"Verification complete. Welcome back, {pending_user.full_name or pending_user.email}.")
        return redirect(resolve_dashboard_url(pending_user))


class LogoutView(LoginRequiredMixin, View):
    def post(self, request):
        record_audit_event(
            actor=request.user,
            event_type="portal_logout",
            entity_type="user",
            entity_id=request.user.pk,
            message=f"Portal logout completed for {request.user.email or request.user.phone_number}.",
        )
        logout(request)
        messages.success(request, "You have been signed out.")
        return redirect("login")


class PortalPasswordResetView(PasswordResetView):
    form_class = UniqueEmailPasswordResetForm
    email_template_name = "registration/password_reset_email.html"
    template_name = "registration/password_reset_form.html"
    subject_template_name = "registration/password_reset_subject.txt"
    success_url = reverse_lazy("password_reset_done")


class PortalPasswordResetDoneView(PasswordResetDoneView):
    template_name = "registration/password_reset_done.html"


class PortalPasswordResetConfirmView(PasswordResetConfirmView):
    form_class = SecurePortalPasswordSetForm
    template_name = "registration/password_reset_confirm.html"
    success_url = reverse_lazy("password_reset_complete")


class PortalPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "registration/password_reset_complete.html"


class DashboardBaseView(RoleRequiredMixin, TemplateView):
    template_name = "dashboards/role_dashboard.html"
    role_key = ""

    def get_dashboard_metrics(self):
        return []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard"] = DASHBOARD_CONTENT[self.role_key]
        context["metrics"] = self.get_dashboard_metrics()
        return context


class CustomerDashboardView(DashboardBaseView):
    allowed_roles = ("customer",)
    role_key = "customer"
    template_name = "dashboards/customer_dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if getattr(request.user, "role", "") == "customer":
            return redirect(resolve_dashboard_url(request.user))
        return response

    def get_dashboard_metrics(self):
        return [
            {"label": "My Orders", "value": Order.objects.filter(user=self.request.user).count()},
            {"label": "My Prescriptions", "value": Prescription.objects.filter(user=self.request.user).count()},
            {"label": "Saved Addresses", "value": CustomerAddress.objects.filter(user=self.request.user).count()},
            {"label": "Saved Payments", "value": SavedPaymentMethod.objects.filter(user=self.request.user, is_active=True).count()},
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        recent_orders = Order.objects.filter(user=self.request.user).order_by("-created_at")[:5]
        recent_prescriptions = Prescription.objects.filter(user=self.request.user).order_by("-created_at")[:5]
        addresses = CustomerAddress.objects.filter(user=self.request.user).order_by("-is_default", "-updated_at")[:4]
        payment_methods = SavedPaymentMethod.objects.filter(user=self.request.user, is_active=True).order_by("-is_default", "-updated_at")[:4]
        notifications = Notification.objects.filter(user=self.request.user).order_by("-created_at")[:5]
        catalog_highlights = Product.objects.filter(is_active=True).order_by("-updated_at")[:4]

        context.update(
            {
                "quick_actions": [
                    {"label": "Browse medicines", "url": "/api/v1/catalog/", "icon": "capsule"},
                    {"label": "My profile API", "url": "/api/v1/auth/me/", "icon": "person-badge"},
                    {"label": "Reset password", "url": "/password-reset/", "icon": "shield-lock"},
                ],
                "recent_orders": recent_orders,
                "recent_prescriptions": recent_prescriptions,
                "addresses": addresses,
                "payment_methods": payment_methods,
                "notifications": notifications,
                "catalog_highlights": catalog_highlights,
                "order_status_summary": [
                    {"label": "Placed", "value": Order.objects.filter(user=self.request.user, status="placed").count()},
                    {"label": "Under review", "value": Order.objects.filter(user=self.request.user, status="pending_prescription_review").count()},
                    {"label": "Confirmed", "value": Order.objects.filter(user=self.request.user, status="confirmed").count()},
                    {"label": "Cancelled", "value": Order.objects.filter(user=self.request.user, status="cancelled").count()},
                ],
            }
        )
        return context


class PharmacistDashboardView(DashboardBaseView):
    allowed_roles = ("pharmacist",)
    role_key = "pharmacist"
    template_name = "dashboards/pharmacist_dashboard.html"

    def get_dashboard_metrics(self):
        today = timezone.localdate()
        return [
            {"label": "Pending Reviews", "value": Prescription.objects.filter(status="pending_review").count()},
            {"label": "Approved Today", "value": Prescription.objects.filter(status="approved", updated_at__date=today).count()},
            {"label": "Clarifications", "value": Prescription.objects.filter(status="clarification_required").count()},
            {"label": "Unread Alerts", "value": Notification.objects.filter(is_read=False).count()},
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        review_queue = Prescription.objects.select_related("user", "reviewed_by").filter(status="pending_review").order_by("-review_priority", "created_at")[:6]
        recent_decisions = Prescription.objects.select_related("user", "reviewed_by").filter(status__in=["approved", "rejected", "clarification_required"]).order_by("-updated_at")[:6]
        my_reviews_today = Prescription.objects.filter(reviewed_by=self.request.user, reviewed_at__date=today)
        alerts = Notification.objects.filter(kind__in=["prescription_update", "system_alert"], is_read=False).order_by("-created_at")[:6]

        context.update(
            {
                "quick_actions": [
                    {"label": "Review queue", "url": "/pharmacist/dashboard/#queue", "icon": "clipboard2-pulse"},
                    {"label": "Unread alerts", "url": "/pharmacist/dashboard/#alerts", "icon": "bell"},
                    {"label": "Profile API", "url": "/api/v1/auth/me/", "icon": "person-badge"},
                ],
                "review_queue": review_queue,
                "recent_decisions": recent_decisions,
                "alerts": alerts,
                "review_summary": [
                    {"label": "Urgent queue", "value": Prescription.objects.filter(status="pending_review", review_priority="urgent").count()},
                    {"label": "High priority", "value": Prescription.objects.filter(status="pending_review", review_priority="high").count()},
                    {"label": "My reviews today", "value": my_reviews_today.count()},
                    {"label": "My approved today", "value": my_reviews_today.filter(status="approved").count()},
                ],
            }
        )
        return context


class VendorDashboardView(DashboardBaseView):
    allowed_roles = ("vendor",)
    role_key = "vendor"
    template_name = "dashboards/vendor_dashboard.html"

    def get_dashboard_metrics(self):
        low_stock = InventoryItem.objects.filter(quantity_on_hand__lte=10).count()
        return [
            {"label": "Active Products", "value": Product.objects.filter(is_active=True).count()},
            {"label": "Inventory Rows", "value": InventoryItem.objects.count()},
            {"label": "Low Stock Items", "value": low_stock},
            {"label": "Confirmed Orders", "value": Order.objects.filter(status="confirmed").count()},
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from platform_apps.inventory.models import StockMovement
        from platform_apps.inventory.services import inventory_risk_snapshot

        inventory_risk = inventory_risk_snapshot()
        recent_movements = StockMovement.objects.select_related("product", "location", "created_by").order_by("-created_at")[:6]
        recent_orders = Order.objects.select_related("user").order_by("-created_at")[:6]
        catalog_highlights = Product.objects.filter(is_active=True).order_by("-updated_at")[:6]

        context.update(
            {
                "quick_actions": [
                    {"label": "Inventory API", "url": "/api/v1/inventory/", "icon": "boxes"},
                    {"label": "Catalog API", "url": "/api/v1/catalog/", "icon": "capsule-pill"},
                    {"label": "Delivery API", "url": "/api/v1/delivery/", "icon": "truck"},
                ],
                "inventory_risk": inventory_risk,
                "recent_movements": recent_movements,
                "recent_orders": recent_orders,
                "catalog_highlights": catalog_highlights,
                "fulfillment_summary": [
                    {"label": "Queued", "value": Order.objects.filter(fulfillment_status="queued").count()},
                    {"label": "Packed", "value": Order.objects.filter(fulfillment_status="packed").count()},
                    {"label": "Shipped", "value": Order.objects.filter(fulfillment_status="shipped").count()},
                    {"label": "Delivered", "value": Order.objects.filter(fulfillment_status="delivered").count()},
                ],
            }
        )
        return context


class VendorStaffDashboardView(DashboardBaseView):
    allowed_roles = ("vendor_staff",)
    role_key = "vendor_staff"
    template_name = "dashboards/vendor_staff_dashboard.html"

    def get_dashboard_metrics(self):
        return [
            {"label": "Assigned Orders", "value": Order.objects.filter(status__in=["placed", "confirmed"]).count()},
            {"label": "Low Stock Rows", "value": InventoryItem.objects.filter(quantity_on_hand__lte=10).count()},
            {"label": "Recent Movements", "value": StockMovement.objects.filter(created_at__gte=timezone.now() - timezone.timedelta(days=1)).count()},
            {"label": "Active Products", "value": Product.objects.filter(is_active=True).count()},
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from platform_apps.inventory.services import inventory_risk_snapshot

        inventory_risk = inventory_risk_snapshot()
        assigned_orders = Order.objects.select_related("user").filter(
            status__in=["placed", "confirmed", "pending_prescription_review"]
        ).order_by("-updated_at", "-created_at")[:8]
        recent_movements = StockMovement.objects.select_related("product", "location", "created_by").order_by("-created_at")[:8]
        low_stock_rows = InventoryItem.objects.select_related("product", "location").filter(quantity_on_hand__lte=10).order_by("quantity_on_hand", "-updated_at")[:8]
        recent_products = Product.objects.filter(is_active=True).order_by("-updated_at")[:8]

        context.update(
            {
                "quick_actions": [
                    {"label": "Orders API", "url": "/api/v1/orders/", "icon": "bag-check"},
                    {"label": "Inventory API", "url": "/api/v1/inventory/", "icon": "boxes"},
                    {"label": "Catalog API", "url": "/api/v1/catalog/", "icon": "capsule-pill"},
                ],
                "counter_snapshot": [
                    {"label": "Placed orders", "value": Order.objects.filter(status="placed").count()},
                    {"label": "Confirmed orders", "value": Order.objects.filter(status="confirmed").count()},
                    {"label": "Pending Rx review", "value": Order.objects.filter(status="pending_prescription_review").count()},
                    {"label": "Notifications", "value": Notification.objects.filter(is_read=False).count()},
                ],
                "inventory_risk": inventory_risk,
                "assigned_orders": assigned_orders,
                "recent_movements": recent_movements,
                "low_stock_rows": low_stock_rows,
                "recent_products": recent_products,
            }
        )
        return context


class WarehouseDashboardView(DashboardBaseView):
    allowed_roles = ("warehouse_operator",)
    role_key = "warehouse_operator"
    template_name = "dashboards/warehouse_dashboard.html"

    def get_dashboard_metrics(self):
        return [
            {"label": "Inventory Rows", "value": InventoryItem.objects.count()},
            {"label": "Low Stock Rows", "value": InventoryItem.objects.filter(quantity_on_hand__lte=10).count()},
            {"label": "Queued Orders", "value": Order.objects.filter(fulfillment_status="queued").count()},
            {"label": "Packed Orders", "value": Order.objects.filter(fulfillment_status="packed").count()},
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from platform_apps.inventory.services import inventory_risk_snapshot

        inventory_risk = inventory_risk_snapshot()
        recent_movements = StockMovement.objects.select_related("product", "location", "created_by").order_by("-created_at")[:8]
        fulfillment_orders = Order.objects.select_related("user").filter(
            fulfillment_status__in=["queued", "packed", "shipped"]
        ).order_by("-updated_at", "-created_at")[:8]

        context.update(
            {
                "quick_actions": [
                    {"label": "Inventory API", "url": "/api/v1/inventory/", "icon": "boxes"},
                    {"label": "Orders API", "url": "/api/v1/orders/", "icon": "box-seam"},
                    {"label": "Delivery API", "url": "/api/v1/delivery/", "icon": "truck"},
                ],
                "inventory_risk": inventory_risk,
                "recent_movements": recent_movements,
                "fulfillment_orders": fulfillment_orders,
                "warehouse_snapshot": [
                    {"label": "Out of stock", "value": inventory_risk.get("out_of_stock_count", 0)},
                    {"label": "Low stock", "value": inventory_risk.get("low_stock_count", 0)},
                    {"label": "Shipped", "value": Order.objects.filter(fulfillment_status="shipped").count()},
                    {"label": "Delivered", "value": Order.objects.filter(fulfillment_status="delivered").count()},
                ],
            }
        )
        return context


class DeliveryDashboardView(DashboardBaseView):
    allowed_roles = ("delivery_agent",)
    role_key = "delivery_agent"
    template_name = "dashboards/delivery_dashboard.html"

    def get_dashboard_metrics(self):
        metrics = delivery_metrics_snapshot()
        return [
            {"label": "Queued", "value": metrics.get("queued_shipments", 0)},
            {"label": "Assigned", "value": metrics.get("assigned_shipments", 0)},
            {"label": "In Transit", "value": metrics.get("in_transit_shipments", 0)},
            {"label": "Delivered", "value": metrics.get("delivered_shipments", 0)},
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        metrics = delivery_metrics_snapshot()
        recent_shipments = DeliveryShipment.objects.select_related("order", "zone").order_by("-updated_at")[:8]
        exception_shipments = DeliveryShipment.objects.select_related("order", "zone").filter(
            status__in=["failed", "returned", "cancelled"]
        ).order_by("-updated_at")[:8]
        event_timeline = DeliveryShipment.objects.select_related("order", "zone").filter(
            status__in=["assigned", "picked_up", "in_transit", "out_for_delivery", "failed"]
        ).order_by("-updated_at")[:8]

        context.update(
            {
                "quick_actions": [
                    {"label": "Delivery API", "url": "/api/v1/delivery/admin/shipments/", "icon": "truck"},
                    {"label": "Orders API", "url": "/api/v1/orders/", "icon": "box-seam"},
                    {"label": "Notifications API", "url": "/api/v1/notifications/", "icon": "bell"},
                ],
                "delivery_snapshot": [
                    {"label": "Dispatch ready", "value": metrics.get("dispatch_ready_shipments", 0)},
                    {"label": "Reattempt due", "value": metrics.get("reattempt_due_shipments", 0)},
                    {"label": "Failed", "value": metrics.get("failed_shipments", 0)},
                    {"label": "Returned", "value": metrics.get("returned_shipments", 0)},
                ],
                "recent_shipments": recent_shipments,
                "exception_shipments": exception_shipments,
                "event_timeline": event_timeline,
            }
        )
        return context


class SupportDashboardView(DashboardBaseView):
    allowed_roles = ("support_agent",)
    role_key = "support_agent"
    template_name = "dashboards/support_dashboard.html"

    def get_dashboard_metrics(self):
        today = timezone.localdate()
        return [
            {"label": "Unread Alerts", "value": Notification.objects.filter(is_read=False).count()},
            {"label": "Orders Today", "value": Order.objects.filter(created_at__date=today).count()},
            {"label": "Pending Rx Review", "value": Prescription.objects.filter(status="pending_review").count()},
            {"label": "Blocked Users", "value": User.objects.filter(account_status="blocked").count()},
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        recent_notifications = Notification.objects.order_by("-created_at")[:8]
        recent_orders = Order.objects.select_related("user").order_by("-created_at")[:8]
        recent_prescriptions = Prescription.objects.select_related("user", "reviewed_by").order_by("-updated_at", "-created_at")[:8]
        customer_signals = [
            {"label": "Active users", "value": User.objects.filter(account_status="active").count()},
            {"label": "Locked accounts", "value": User.objects.filter(account_locked=True).count()},
            {"label": "Suspended users", "value": User.objects.filter(account_status="suspended").count()},
            {"label": "Pending email verification", "value": User.objects.filter(email_verified=False, deleted_at__isnull=True).count()},
        ]

        context.update(
            {
                "quick_actions": [
                    {"label": "Users API", "url": "/api/v1/auth/admin/users/", "icon": "people"},
                    {"label": "Orders API", "url": "/api/v1/orders/", "icon": "bag-check"},
                    {"label": "Notifications API", "url": "/api/v1/notifications/", "icon": "bell"},
                ],
                "customer_signals": customer_signals,
                "recent_notifications": recent_notifications,
                "recent_orders": recent_orders,
                "recent_prescriptions": recent_prescriptions,
            }
        )
        return context


class FinanceDashboardView(DashboardBaseView):
    allowed_roles = ("finance",)
    role_key = "finance"
    template_name = "dashboards/finance_dashboard.html"

    def get_dashboard_metrics(self):
        paid_revenue = Order.objects.filter(payment_status="paid").aggregate(total=Sum("total")).get("total") or 0
        captured_total = PaymentAttempt.objects.filter(status="captured").aggregate(total=Sum("amount")).get("total") or 0
        pending_refunds = RefundRequest.objects.filter(status__in=["requested", "approved"]).count()
        failed_payments = PaymentAttempt.objects.filter(status="failed").count()
        return [
            {"label": "Paid Revenue", "value": f"{paid_revenue:,.2f}"},
            {"label": "Captured", "value": f"{captured_total:,.2f}"},
            {"label": "Pending Refunds", "value": pending_refunds},
            {"label": "Failed Payments", "value": failed_payments},
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        refunded_total = RefundRequest.objects.filter(status="processed").aggregate(total=Sum("amount")).get("total") or 0
        refund_snapshot = [
            {"label": "Requested", "value": RefundRequest.objects.filter(status="requested").count()},
            {"label": "Approved", "value": RefundRequest.objects.filter(status="approved").count()},
            {"label": "Processed", "value": RefundRequest.objects.filter(status="processed").count()},
            {"label": "Rejected", "value": RefundRequest.objects.filter(status="rejected").count()},
        ]
        revenue_snapshot = [
            {"label": "Paid orders", "value": Order.objects.filter(payment_status="paid").count()},
            {"label": "Refunded total", "value": f"{refunded_total:,.2f}"},
            {"label": "Captured attempts", "value": PaymentAttempt.objects.filter(status="captured").count()},
            {"label": "Pending payments", "value": PaymentAttempt.objects.filter(status__in=["created", "pending", "authorized"]).count()},
        ]
        recent_payments = PaymentAttempt.objects.select_related("order").order_by("-initiated_at")[:8]
        recent_refunds = RefundRequest.objects.select_related("order", "payment_attempt", "requested_by").order_by("-updated_at", "-created_at")[:8]
        settlement_batches = SettlementBatch.objects.order_by("-created_at")[:8]

        context.update(
            {
                "quick_actions": [
                    {"label": "Orders API", "url": "/api/v1/orders/admin-orders/", "icon": "bag-check"},
                    {"label": "Reconciliation Admin", "url": "/admin/orders/reconciliationsnapshot/", "icon": "receipt-cutoff"},
                    {"label": "Payment Attempts Admin", "url": "/admin/orders/paymentattempt/", "icon": "credit-card-2-front"},
                ],
                "revenue_snapshot": revenue_snapshot,
                "refund_snapshot": refund_snapshot,
                "recent_payments": recent_payments,
                "recent_refunds": recent_refunds,
                "settlement_batches": settlement_batches,
            }
        )
        return context


class SecurityAdminDashboardView(DashboardBaseView):
    allowed_roles = ("security_admin",)
    role_key = "security_admin"
    template_name = "dashboards/security_dashboard.html"

    def get_dashboard_metrics(self):
        from platform_apps.audit.models import AuditLog

        last_24_hours = timezone.now() - timezone.timedelta(hours=24)
        return [
            {"label": "Failed Logins 24h", "value": AuditLog.objects.filter(event_type="portal_login_failed", created_at__gte=last_24_hours).count()},
            {"label": "Critical Events 24h", "value": AuditLog.objects.filter(severity="critical", created_at__gte=last_24_hours).count()},
            {"label": "Locked Accounts", "value": User.objects.filter(account_locked=True).count()},
            {"label": "MFA Enabled", "value": User.objects.filter(mfa_enabled=True, deleted_at__isnull=True).count()},
        ]

    def get_context_data(self, **kwargs):
        from platform_apps.audit.models import AuditLog

        context = super().get_context_data(**kwargs)
        last_24_hours = timezone.now() - timezone.timedelta(hours=24)
        login_risk_snapshot = [
            {"label": "Failed logins 24h", "value": AuditLog.objects.filter(event_type="portal_login_failed", created_at__gte=last_24_hours).count()},
            {"label": "MFA verified 24h", "value": AuditLog.objects.filter(event_type="portal_mfa_verified", created_at__gte=last_24_hours).count()},
            {"label": "Accounts locked", "value": User.objects.filter(account_locked=True).count()},
            {"label": "High retry accounts", "value": User.objects.filter(failed_login_attempts__gte=3, deleted_at__isnull=True).count()},
        ]
        account_control_snapshot = [
            {"label": "Blocked users", "value": User.objects.filter(account_status="blocked", deleted_at__isnull=True).count()},
            {"label": "Suspended users", "value": User.objects.filter(account_status="suspended", deleted_at__isnull=True).count()},
            {"label": "Email unverified", "value": User.objects.filter(email_verified=False, deleted_at__isnull=True).count()},
            {"label": "MFA disabled", "value": User.objects.filter(mfa_enabled=False, deleted_at__isnull=True).count()},
        ]
        recent_security_events = AuditLog.objects.select_related("actor").filter(
            Q(event_type__in=["portal_login_failed", "portal_mfa_failed", "portal_mfa_verified", "user_account_locked"])
            | Q(severity__in=["warning", "critical"])
        ).order_by("-created_at")[:8]
        recent_control_actions = AuditLog.objects.select_related("actor").filter(
            event_type__in=[
                "user_account_locked",
                "user_account_unlocked",
                "user_password_reset",
                "user_resend_verification_email",
                "user_activated",
                "user_deactivated",
                "user_deleted",
            ]
        ).order_by("-created_at")[:8]
        access_watchlist = User.objects.filter(
            Q(account_locked=True)
            | Q(account_status__in=["blocked", "suspended"])
            | Q(failed_login_attempts__gte=3)
        ).order_by("-updated_at")[:8]

        context.update(
            {
                "quick_actions": [
                    {"label": "Users API", "url": "/api/v1/auth/admin/users/", "icon": "people"},
                    {"label": "Audit Admin", "url": "/admin/audit/auditlog/", "icon": "journal-lock"},
                    {"label": "Approval Queue", "url": "/admin/approval-queue/", "icon": "clipboard-check"},
                ],
                "login_risk_snapshot": login_risk_snapshot,
                "account_control_snapshot": account_control_snapshot,
                "recent_security_events": recent_security_events,
                "recent_control_actions": recent_control_actions,
                "access_watchlist": access_watchlist,
            }
        )
        return context


class DoctorDashboardView(DashboardBaseView):
    allowed_roles = ("doctor",)
    role_key = "doctor"
    template_name = "dashboards/doctor_dashboard.html"

    def get_dashboard_metrics(self):
        doctor_linked_queryset = Prescription.objects.exclude(doctor_name__exact="")
        return [
            {"label": "Doctor-linked Rx", "value": doctor_linked_queryset.count()},
            {"label": "Distinct Doctors", "value": doctor_linked_queryset.values("doctor_name").distinct().count()},
            {"label": "Pending Review", "value": Prescription.objects.filter(status="pending_review").count()},
            {"label": "Clarifications", "value": Prescription.objects.filter(status="clarification_required").count()},
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor_linked_queryset = Prescription.objects.exclude(doctor_name__exact="")
        clinical_snapshot = [
            {"label": "Submitted", "value": Prescription.objects.filter(status="submitted").count()},
            {"label": "Pending review", "value": Prescription.objects.filter(status="pending_review").count()},
            {"label": "Approved", "value": Prescription.objects.filter(status="approved").count()},
            {"label": "Rejected", "value": Prescription.objects.filter(status="rejected").count()},
        ]
        doctor_activity = (
            doctor_linked_queryset.values("doctor_name")
            .annotate(case_count=Count("id"))
            .order_by("-case_count", "doctor_name")[:8]
        )
        recent_cases = doctor_linked_queryset.select_related("user", "reviewed_by").order_by("-updated_at", "-created_at")[:8]

        context.update(
            {
                "quick_actions": [
                    {"label": "Prescriptions API", "url": "/api/v1/prescriptions/", "icon": "file-earmark-medical"},
                    {"label": "Orders API", "url": "/api/v1/orders/", "icon": "bag-check"},
                    {"label": "Notifications API", "url": "/api/v1/notifications/", "icon": "bell"},
                ],
                "clinical_snapshot": clinical_snapshot,
                "doctor_activity": doctor_activity,
                "recent_cases": recent_cases,
            }
        )
        return context


class OperationsManagerDashboardView(DashboardBaseView):
    allowed_roles = ("operations_manager",)
    role_key = "operations_manager"
    template_name = "dashboards/operations_dashboard.html"

    def get_dashboard_metrics(self):
        return [
            {"label": "Pending Approvals", "value": User.objects.filter(approval_status="pending").count()},
            {"label": "Open Orders", "value": Order.objects.filter(status__in=["placed", "pending_prescription_review", "confirmed"]).count()},
            {"label": "Low Stock Rows", "value": InventoryItem.objects.filter(quantity_on_hand__lte=10).count()},
            {"label": "Active Shipments", "value": DeliveryShipment.objects.filter(status__in=["queued", "assigned", "picked_up", "in_transit", "out_for_delivery"]).count()},
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        approval_snapshot = [
            {"label": "Pending approvals", "value": User.objects.filter(approval_status="pending").count()},
            {"label": "Overdue reviews", "value": User.objects.filter(approval_status="pending", approval_due_at__lt=timezone.now()).count()},
            {"label": "Unassigned requests", "value": User.objects.filter(approval_status="pending", approval_assigned_to__isnull=True).count()},
            {
                "label": "Rejected documents",
                "value": User.objects.filter(approval_status="pending").filter(
                    Q(role="vendor", vendor_license_document_status="rejected")
                    | Q(role="pharmacist", pharmacist_registration_document_status="rejected")
                ).count(),
            },
        ]
        order_snapshot = [
            {"label": "Placed", "value": Order.objects.filter(status="placed").count()},
            {"label": "Pending Rx review", "value": Order.objects.filter(status="pending_prescription_review").count()},
            {"label": "Confirmed", "value": Order.objects.filter(status="confirmed").count()},
            {"label": "Cancelled", "value": Order.objects.filter(status="cancelled").count()},
        ]
        fulfillment_snapshot = [
            {"label": "Low stock", "value": InventoryItem.objects.filter(quantity_on_hand__lte=10).count()},
            {"label": "Queued shipments", "value": DeliveryShipment.objects.filter(status="queued").count()},
            {"label": "In transit", "value": DeliveryShipment.objects.filter(status="in_transit").count()},
            {"label": "Failed deliveries", "value": DeliveryShipment.objects.filter(status="failed").count()},
        ]
        pending_approval_users = (
            User.objects.filter(approval_status="pending")
            .select_related("approval_assigned_to")
            .order_by("approval_due_at", "-created_at")[:8]
        )
        recent_orders = Order.objects.select_related("user").order_by("-created_at")[:8]
        top_inventory_risks = InventoryItem.objects.select_related("product", "location").order_by("quantity_on_hand", "-updated_at")[:8]
        delivery_queue = DeliveryShipment.objects.select_related("order", "zone").filter(
            status__in=["queued", "assigned", "picked_up", "in_transit", "out_for_delivery", "failed"]
        ).order_by("-updated_at")[:8]

        context.update(
            {
                "quick_actions": [
                    {"label": "Approval Queue", "url": "/admin/approval-queue/", "icon": "clipboard-check"},
                    {"label": "Orders API", "url": "/api/v1/orders/", "icon": "bag-check"},
                    {"label": "Delivery API", "url": "/api/v1/delivery/admin/shipments/", "icon": "truck"},
                ],
                "approval_snapshot": approval_snapshot,
                "order_snapshot": order_snapshot,
                "fulfillment_snapshot": fulfillment_snapshot,
                "pending_approval_users": pending_approval_users,
                "recent_orders": recent_orders,
                "top_inventory_risks": top_inventory_risks,
                "delivery_queue": delivery_queue,
            }
        )
        return context


class CatalogManagerDashboardView(DashboardBaseView):
    allowed_roles = ("catalog_manager",)
    role_key = "catalog_manager"
    template_name = "dashboards/catalog_dashboard.html"

    def get_dashboard_metrics(self):
        return [
            {"label": "Active Products", "value": Product.objects.filter(is_active=True).count()},
            {"label": "Categories", "value": Category.objects.filter(is_active=True).count()},
            {"label": "Brands", "value": Brand.objects.filter(is_active=True).count()},
            {"label": "Substitute Links", "value": ProductSubstitute.objects.count()},
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        coverage_snapshot = [
            {"label": "Prescription items", "value": Product.objects.filter(is_active=True, requires_prescription=True).count()},
            {"label": "OTC items", "value": Product.objects.filter(is_active=True, is_otc=True).count()},
            {"label": "In stock", "value": Product.objects.filter(is_active=True, stock_status="in_stock").count()},
            {"label": "Out of stock", "value": Product.objects.filter(is_active=True, stock_status="out_of_stock").count()},
        ]
        structure_snapshot = [
            {"label": "Active categories", "value": Category.objects.filter(is_active=True).count()},
            {"label": "Active brands", "value": Brand.objects.filter(is_active=True).count()},
            {"label": "Inactive products", "value": Product.objects.filter(is_active=False).count()},
            {"label": "Low stock tags", "value": Product.objects.filter(is_active=True, stock_status="low_stock").count()},
        ]
        recent_products = Product.objects.select_related("category", "brand").order_by("-updated_at", "-created_at")[:8]
        top_categories = Category.objects.annotate(product_count=Count("products")).order_by("-product_count", "name")[:8]
        recent_substitutes = ProductSubstitute.objects.select_related("source_product", "substitute_product").order_by("-created_at")[:8]

        context.update(
            {
                "quick_actions": [
                    {"label": "Catalog API", "url": "/api/v1/catalog/products/", "icon": "capsule-pill"},
                    {"label": "Products Admin", "url": "/admin/catalog/product/", "icon": "box-seam"},
                    {"label": "Categories Admin", "url": "/admin/catalog/category/", "icon": "diagram-3"},
                ],
                "coverage_snapshot": coverage_snapshot,
                "structure_snapshot": structure_snapshot,
                "recent_products": recent_products,
                "top_categories": top_categories,
                "recent_substitutes": recent_substitutes,
            }
        )
        return context


class ProcurementManagerDashboardView(DashboardBaseView):
    allowed_roles = ("procurement_manager",)
    role_key = "procurement_manager"
    template_name = "dashboards/procurement_dashboard.html"

    def get_dashboard_metrics(self):
        from platform_apps.inventory.services import inventory_risk_snapshot

        inventory_risk = inventory_risk_snapshot(limit=8)
        inbound_total = InventoryItem.objects.aggregate(total=Sum("inbound_quantity")).get("total") or 0
        return [
            {"label": "Low Stock", "value": inventory_risk.get("low_stock_count", 0)},
            {"label": "Out of Stock", "value": inventory_risk.get("out_of_stock_count", 0)},
            {"label": "Inbound Units", "value": inbound_total},
            {"label": "Low Stock Rules", "value": LowStockRule.objects.count()},
        ]

    def get_context_data(self, **kwargs):
        from platform_apps.inventory.services import inventory_risk_snapshot

        context = super().get_context_data(**kwargs)
        inventory_risk = inventory_risk_snapshot(limit=8)
        inbound_snapshot = [
            {"label": "Total inbound", "value": InventoryItem.objects.aggregate(total=Sum("inbound_quantity")).get("total") or 0},
            {"label": "Rows with inbound", "value": InventoryItem.objects.filter(inbound_quantity__gt=0).count()},
            {"label": "Warehouse rows", "value": InventoryItem.objects.filter(location__kind="warehouse").count()},
            {"label": "Pharmacy rows", "value": InventoryItem.objects.filter(location__kind="pharmacy").count()},
        ]
        replenishment_rows = (
            InventoryItem.objects.select_related("product", "location")
            .filter(Q(quantity_on_hand__lte=10) | Q(product__stock_status__in=["low_stock", "out_of_stock"]))
            .order_by("quantity_on_hand", "-inbound_quantity", "product__name")[:8]
        )
        recent_restocks = StockMovement.objects.select_related("product", "location", "created_by").filter(
            movement_type__in=["restock", "transfer_in", "manual_count"]
        ).order_by("-created_at")[:8]

        context.update(
            {
                "quick_actions": [
                    {"label": "Inventory API", "url": "/api/v1/inventory/", "icon": "boxes"},
                    {"label": "Inventory Admin", "url": "/admin/inventory/inventoryitem/", "icon": "box-seam"},
                    {"label": "Low Stock Rules", "url": "/admin/inventory/lowstockrule/", "icon": "sliders"},
                ],
                "inventory_risk": inventory_risk,
                "inbound_snapshot": inbound_snapshot,
                "replenishment_rows": replenishment_rows,
                "recent_restocks": recent_restocks,
            }
        )
        return context


class MarketingManagerDashboardView(DashboardBaseView):
    allowed_roles = ("marketing_manager",)
    role_key = "marketing_manager"
    template_name = "dashboards/marketing_dashboard.html"

    def get_dashboard_metrics(self):
        today = timezone.localdate()
        week_start = today - timezone.timedelta(days=6)
        return [
            {"label": "Active Customers", "value": CustomerWebsiteActivityDaily.objects.filter(activity_date=today, active_seconds__gt=0).count()},
            {"label": "Weekly Sessions", "value": CustomerWebsiteActivityDaily.objects.filter(activity_date__gte=week_start).aggregate(total=Sum("heartbeat_count")).get("total") or 0},
            {"label": "Orders 7d", "value": Order.objects.filter(created_at__date__gte=week_start).count()},
            {"label": "Prescriptions 7d", "value": Prescription.objects.filter(created_at__date__gte=week_start).count()},
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        week_start = today - timezone.timedelta(days=6)
        audience_snapshot = [
            {"label": "Today active users", "value": CustomerWebsiteActivityDaily.objects.filter(activity_date=today, active_seconds__gt=0).count()},
            {"label": "Today active mins", "value": (CustomerWebsiteActivityDaily.objects.filter(activity_date=today).aggregate(total=Sum("active_seconds")).get("total") or 0) // 60},
            {"label": "Weekly heartbeats", "value": CustomerWebsiteActivityDaily.objects.filter(activity_date__gte=week_start).aggregate(total=Sum("heartbeat_count")).get("total") or 0},
            {"label": "Unread notifications", "value": Notification.objects.filter(is_read=False).count()},
        ]
        demand_snapshot = [
            {"label": "Orders 7d", "value": Order.objects.filter(created_at__date__gte=week_start).count()},
            {"label": "Paid orders 7d", "value": Order.objects.filter(created_at__date__gte=week_start, payment_status="paid").count()},
            {"label": "Prescriptions 7d", "value": Prescription.objects.filter(created_at__date__gte=week_start).count()},
            {"label": "New customers 7d", "value": User.objects.filter(role="customer", created_at__date__gte=week_start).count()},
        ]
        recent_activity = (
            CustomerWebsiteActivityDaily.objects.select_related("user")
            .filter(activity_date__gte=week_start, active_seconds__gt=0)
            .order_by("-activity_date", "-active_seconds")[:8]
        )
        category_mix = Category.objects.filter(is_active=True).annotate(product_count=Count("products")).order_by("-product_count", "name")[:8]
        catalog_focus = Product.objects.select_related("category", "brand").filter(is_active=True).order_by("-updated_at")[:8]

        context.update(
            {
                "quick_actions": [
                    {"label": "Catalog API", "url": "/api/v1/catalog/products/", "icon": "capsule-pill"},
                    {"label": "Categories API", "url": "/api/v1/catalog/categories/", "icon": "diagram-3"},
                    {"label": "Notifications API", "url": "/api/v1/notifications/", "icon": "bell"},
                ],
                "audience_snapshot": audience_snapshot,
                "demand_snapshot": demand_snapshot,
                "recent_activity": recent_activity,
                "category_mix": category_mix,
                "catalog_focus": catalog_focus,
            }
        )
        return context


class ComplianceOfficerDashboardView(DashboardBaseView):
    allowed_roles = ("compliance_officer",)
    role_key = "compliance_officer"
    template_name = "dashboards/compliance_dashboard.html"

    def get_dashboard_metrics(self):
        from platform_apps.audit.models import AuditLog

        last_24_hours = timezone.now() - timezone.timedelta(hours=24)
        rejected_documents = User.objects.filter(
            approval_status="pending",
        ).filter(
            Q(role="vendor", vendor_license_document_status="rejected")
            | Q(role="pharmacist", pharmacist_registration_document_status="rejected")
        ).count()
        return [
            {"label": "Critical Audit 24h", "value": AuditLog.objects.filter(severity="critical", created_at__gte=last_24_hours).count()},
            {"label": "Rejected Documents", "value": rejected_documents},
            {"label": "Clarification Rx", "value": Prescription.objects.filter(status="clarification_required").count()},
            {"label": "Overdue Approvals", "value": User.objects.filter(approval_status="pending", approval_due_at__lt=timezone.now()).count()},
        ]

    def get_context_data(self, **kwargs):
        from platform_apps.audit.models import AuditLog

        context = super().get_context_data(**kwargs)
        last_24_hours = timezone.now() - timezone.timedelta(hours=24)
        audit_snapshot = [
            {"label": "Warnings 24h", "value": AuditLog.objects.filter(severity="warning", created_at__gte=last_24_hours).count()},
            {"label": "Critical 24h", "value": AuditLog.objects.filter(severity="critical", created_at__gte=last_24_hours).count()},
            {"label": "Approval changes 24h", "value": AuditLog.objects.filter(event_type="approval_status_changed", created_at__gte=last_24_hours).count()},
            {"label": "Document changes 24h", "value": AuditLog.objects.filter(event_type="approval_document_status_changed", created_at__gte=last_24_hours).count()},
        ]
        approval_exceptions = [
            {"label": "Pending approvals", "value": User.objects.filter(approval_status="pending").count()},
            {"label": "Overdue approvals", "value": User.objects.filter(approval_status="pending", approval_due_at__lt=timezone.now()).count()},
            {
                "label": "Rejected vendor docs",
                "value": User.objects.filter(approval_status="pending", role="vendor", vendor_license_document_status="rejected").count(),
            },
            {
                "label": "Rejected pharmacist docs",
                "value": User.objects.filter(approval_status="pending", role="pharmacist", pharmacist_registration_document_status="rejected").count(),
            },
        ]
        clinical_risk = [
            {"label": "Pending review", "value": Prescription.objects.filter(status="pending_review").count()},
            {"label": "Clarification required", "value": Prescription.objects.filter(status="clarification_required").count()},
            {"label": "Rejected", "value": Prescription.objects.filter(status="rejected").count()},
            {"label": "Approved today", "value": Prescription.objects.filter(status="approved", updated_at__date=timezone.localdate()).count()},
        ]
        recent_audit = AuditLog.objects.select_related("actor").filter(
            Q(severity__in=["warning", "critical"])
            | Q(event_type__in=["approval_status_changed", "approval_document_status_changed", "prescription_reviewed"])
        ).order_by("-created_at")[:8]
        flagged_users = User.objects.filter(
            Q(approval_status="pending", approval_due_at__lt=timezone.now())
            | Q(role="vendor", vendor_license_document_status="rejected")
            | Q(role="pharmacist", pharmacist_registration_document_status="rejected")
            | Q(account_status__in=["blocked", "suspended"])
        ).order_by("-updated_at")[:8]
        recent_prescriptions = Prescription.objects.select_related("user", "reviewed_by").filter(
            status__in=["clarification_required", "rejected", "approved", "pending_review"]
        ).order_by("-updated_at", "-created_at")[:8]

        context.update(
            {
                "quick_actions": [
                    {"label": "Audit Admin", "url": "/admin/audit/auditlog/", "icon": "journal-check"},
                    {"label": "Approval Queue", "url": "/admin/approval-queue/", "icon": "clipboard-check"},
                    {"label": "Prescriptions API", "url": "/api/v1/prescriptions/", "icon": "file-earmark-medical"},
                ],
                "audit_snapshot": audit_snapshot,
                "approval_exceptions": approval_exceptions,
                "clinical_risk": clinical_risk,
                "recent_audit": recent_audit,
                "flagged_users": flagged_users,
                "recent_prescriptions": recent_prescriptions,
            }
        )
        return context


class AuditorDashboardView(DashboardBaseView):
    allowed_roles = ("auditor",)
    role_key = "auditor"
    template_name = "dashboards/auditor_dashboard.html"

    def get_dashboard_metrics(self):
        from platform_apps.audit.models import AuditLog

        last_24_hours = timezone.now() - timezone.timedelta(hours=24)
        return [
            {"label": "Audit Events 24h", "value": AuditLog.objects.filter(created_at__gte=last_24_hours).count()},
            {"label": "Warnings 24h", "value": AuditLog.objects.filter(severity="warning", created_at__gte=last_24_hours).count()},
            {"label": "Critical 24h", "value": AuditLog.objects.filter(severity="critical", created_at__gte=last_24_hours).count()},
            {"label": "Approval Logs 24h", "value": AuditLog.objects.filter(event_type__in=["approval_status_changed", "approval_document_status_changed", "approval_sla_escalated"], created_at__gte=last_24_hours).count()},
        ]

    def get_context_data(self, **kwargs):
        from platform_apps.audit.models import AuditLog

        context = super().get_context_data(**kwargs)
        last_24_hours = timezone.now() - timezone.timedelta(hours=24)
        evidence_snapshot = [
            {"label": "Audit events 24h", "value": AuditLog.objects.filter(created_at__gte=last_24_hours).count()},
            {"label": "Warnings 24h", "value": AuditLog.objects.filter(severity="warning", created_at__gte=last_24_hours).count()},
            {"label": "Critical 24h", "value": AuditLog.objects.filter(severity="critical", created_at__gte=last_24_hours).count()},
            {"label": "File events 24h", "value": AuditLog.objects.filter(event_type__in=["file_uploaded", "file_updated", "file_deleted"], created_at__gte=last_24_hours).count()},
        ]
        operations_trace = [
            {"label": "Order admin updates", "value": AuditLog.objects.filter(event_type="admin_order_updated").count()},
            {"label": "Prescription reviews", "value": AuditLog.objects.filter(event_type="prescription_reviewed").count()},
            {"label": "Inventory adjusted", "value": AuditLog.objects.filter(event_type="inventory_adjusted").count()},
            {"label": "Delivery updates", "value": AuditLog.objects.filter(event_type="delivery_shipment_updated").count()},
        ]
        approval_trail = [
            {"label": "Approval status changed", "value": AuditLog.objects.filter(event_type="approval_status_changed").count()},
            {"label": "Document decisions", "value": AuditLog.objects.filter(event_type="approval_document_status_changed").count()},
            {"label": "SLA escalations", "value": AuditLog.objects.filter(event_type="approval_sla_escalated").count()},
            {"label": "Assignments changed", "value": AuditLog.objects.filter(event_type="approval_assignment_changed").count()},
        ]
        recent_evidence = AuditLog.objects.select_related("actor").order_by("-created_at")[:8]
        recent_operations = AuditLog.objects.select_related("actor").filter(
            event_type__in=["admin_order_updated", "prescription_reviewed", "inventory_adjusted", "delivery_shipment_updated"]
        ).order_by("-created_at")[:8]
        recent_approvals = AuditLog.objects.select_related("actor").filter(
            event_type__in=["approval_status_changed", "approval_document_status_changed", "approval_sla_escalated", "approval_assignment_changed"]
        ).order_by("-created_at")[:8]

        context.update(
            {
                "quick_actions": [
                    {"label": "Audit Admin", "url": "/admin/audit/auditlog/", "icon": "journal-text"},
                    {"label": "Managed Files", "url": "/admin/audit/managedfile/", "icon": "folder2-open"},
                    {"label": "Approval Queue", "url": "/admin/approval-queue/", "icon": "clipboard-check"},
                ],
                "evidence_snapshot": evidence_snapshot,
                "operations_trace": operations_trace,
                "approval_trail": approval_trail,
                "recent_evidence": recent_evidence,
                "recent_operations": recent_operations,
                "recent_approvals": recent_approvals,
            }
        )
        return context


class ViewerDashboardView(DashboardBaseView):
    allowed_roles = ("viewer",)
    role_key = "viewer"
    template_name = "dashboards/viewer_dashboard.html"

    def get_dashboard_metrics(self):
        today = timezone.localdate()
        return [
            {"label": "Active Users", "value": User.objects.filter(account_status="active").count()},
            {"label": "Orders Today", "value": Order.objects.filter(created_at__date=today).count()},
            {"label": "Pending Rx Review", "value": Prescription.objects.filter(status="pending_review").count()},
            {"label": "Unread Alerts", "value": Notification.objects.filter(is_read=False).count()},
        ]

    def get_context_data(self, **kwargs):
        from platform_apps.audit.models import AuditLog

        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        last_7_days = timezone.now() - timezone.timedelta(days=7)
        last_24_hours = timezone.now() - timezone.timedelta(hours=24)

        platform_snapshot = [
            {"label": "Total users", "value": User.objects.count()},
            {"label": "Active users", "value": User.objects.filter(account_status="active").count()},
            {"label": "Orders total", "value": Order.objects.count()},
            {"label": "Prescriptions total", "value": Prescription.objects.count()},
        ]
        order_snapshot = [
            {"label": "Placed", "value": Order.objects.filter(status="placed").count()},
            {"label": "Pending Rx review", "value": Order.objects.filter(status="pending_prescription_review").count()},
            {"label": "Confirmed", "value": Order.objects.filter(status="confirmed").count()},
            {"label": "Cancelled", "value": Order.objects.filter(status="cancelled").count()},
        ]
        prescription_snapshot = [
            {"label": "Pending review", "value": Prescription.objects.filter(status="pending_review").count()},
            {"label": "Clarifications", "value": Prescription.objects.filter(status="clarification_required").count()},
            {"label": "Approved today", "value": Prescription.objects.filter(status="approved", updated_at__date=today).count()},
            {"label": "Rejected", "value": Prescription.objects.filter(status="rejected").count()},
        ]
        alert_snapshot = [
            {"label": "Unread notifications", "value": Notification.objects.filter(is_read=False).count()},
            {"label": "Warnings 24h", "value": AuditLog.objects.filter(severity="warning", created_at__gte=last_24_hours).count()},
            {"label": "Critical 24h", "value": AuditLog.objects.filter(severity="critical", created_at__gte=last_24_hours).count()},
            {"label": "Low stock items", "value": InventoryItem.objects.filter(quantity_on_hand__lte=0).count()},
        ]
        recent_orders = Order.objects.select_related("user").order_by("-created_at")[:8]
        recent_prescriptions = Prescription.objects.select_related("user", "reviewed_by").order_by("-updated_at", "-created_at")[:8]
        recent_alerts = Notification.objects.select_related("user").order_by("-created_at")[:8]
        inventory_watch = InventoryItem.objects.select_related("product", "location").order_by("quantity_on_hand", "-updated_at")[:8]
        activity_window = [
            {"label": "Sessions this week", "value": CustomerWebsiteActivityDaily.objects.filter(activity_date__gte=today - timezone.timedelta(days=6)).count()},
            {"label": "Active minutes this week", "value": format_active_duration(CustomerWebsiteActivityDaily.objects.filter(activity_date__gte=today - timezone.timedelta(days=6)).aggregate(total=Sum("active_seconds"))["total"] or 0)},
            {"label": "Orders 7d", "value": Order.objects.filter(created_at__gte=last_7_days).count()},
            {"label": "Prescriptions 7d", "value": Prescription.objects.filter(created_at__gte=last_7_days).count()},
        ]

        context.update(
            {
                "quick_actions": [
                    {"label": "Orders API", "url": "/api/v1/orders/", "icon": "bag-check"},
                    {"label": "Notifications API", "url": "/api/v1/notifications/", "icon": "bell"},
                    {"label": "Health Live", "url": "/api/v1/health/live/", "icon": "activity"},
                ],
                "platform_snapshot": platform_snapshot,
                "order_snapshot": order_snapshot,
                "prescription_snapshot": prescription_snapshot,
                "alert_snapshot": alert_snapshot,
                "recent_orders": recent_orders,
                "recent_prescriptions": recent_prescriptions,
                "recent_alerts": recent_alerts,
                "inventory_watch": inventory_watch,
                "activity_window": activity_window,
            }
        )
        return context


class AdminDashboardView(DashboardBaseView):
    allowed_roles = (
        "admin",
    )
    role_key = "admin"
    template_name = "dashboards/admin_dashboard.html"

    def get_dashboard_metrics(self):
        active_users = User.objects.filter(account_status="active").count()
        return [
            {"label": "Users", "value": User.objects.count()},
            {"label": "Active Users", "value": active_users},
            {"label": "Pending Approvals", "value": User.objects.filter(approval_status="pending").count()},
            {"label": "Orders", "value": Order.objects.count()},
            {"label": "Prescriptions", "value": Prescription.objects.count()},
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from platform_apps.audit.models import AuditLog

        today = timezone.localdate()

        pending_approval_users = (
            User.objects.filter(approval_status="pending")
            .select_related("approval_assigned_to")
            .order_by("approval_due_at", "-created_at")[:6]
        )
        recent_orders = Order.objects.select_related("user").order_by("-created_at")[:6]
        recent_prescriptions = Prescription.objects.select_related("user", "reviewed_by").order_by("-created_at")[:6]
        recent_audit = AuditLog.objects.select_related("actor").filter(severity__in=["warning", "critical"]).order_by("-created_at")[:6]
        my_notifications = Notification.objects.filter(user=self.request.user).order_by("-created_at")[:5]
        rejected_document_count = User.objects.filter(
            approval_status="pending",
        ).filter(
            role="vendor",
            vendor_license_document_status="rejected",
        ).count() + User.objects.filter(
            approval_status="pending",
            role="pharmacist",
            pharmacist_registration_document_status="rejected",
        ).count()

        context.update(
            {
                "quick_actions": [
                    {"label": "Approval Queue", "url": "/admin/approval-queue/", "icon": "clipboard-check", "tone": "primary"},
                    {"label": "Reviewer Schedules", "url": "/admin/reviewer-schedules/", "icon": "calendar3", "tone": "outline-dark"},
                    {"label": "Live Operations Feed", "url": "/admin/live/", "icon": "broadcast", "tone": "outline-dark"},
                ],
                "approval_snapshot": [
                    {"label": "Pending approvals", "value": User.objects.filter(approval_status="pending").count(), "hint": "Accounts waiting for a decision."},
                    {"label": "Overdue reviews", "value": User.objects.filter(approval_status="pending", approval_due_at__lt=timezone.now()).count(), "hint": "Approvals that crossed SLA."},
                    {"label": "Unassigned requests", "value": User.objects.filter(approval_status="pending", approval_assigned_to__isnull=True).count(), "hint": "Pending work with no owner."},
                    {"label": "Rejected documents", "value": rejected_document_count, "hint": "Proof files that need rework."},
                ],
                "order_snapshot": [
                    {"label": "Placed", "value": Order.objects.filter(status="placed").count()},
                    {"label": "Pending Rx review", "value": Order.objects.filter(status="pending_prescription_review").count()},
                    {"label": "Confirmed", "value": Order.objects.filter(status="confirmed").count()},
                    {"label": "Cancelled", "value": Order.objects.filter(status="cancelled").count()},
                ],
                "prescription_snapshot": [
                    {"label": "Pending review", "value": Prescription.objects.filter(status="pending_review").count()},
                    {"label": "Clarifications", "value": Prescription.objects.filter(status="clarification_required").count()},
                    {"label": "Approved today", "value": Prescription.objects.filter(status="approved", updated_at__date=today).count()},
                    {"label": "Rejected", "value": Prescription.objects.filter(status="rejected").count()},
                ],
                "account_health": [
                    {"label": "Active users", "value": User.objects.filter(account_status="active").count()},
                    {"label": "Blocked users", "value": User.objects.filter(account_status="blocked").count()},
                    {"label": "Suspended users", "value": User.objects.filter(account_status="suspended").count()},
                    {"label": "Staff admins", "value": User.objects.filter(role="admin").count()},
                ],
                "pending_approval_users": pending_approval_users,
                "recent_orders": recent_orders,
                "recent_prescriptions": recent_prescriptions,
                "recent_audit": recent_audit,
                "my_notifications": my_notifications,
            }
        )
        return context


class SuperAdminDashboardView(DashboardBaseView):
    allowed_roles = ("super_admin",)
    role_key = "super_admin"
    template_name = "dashboards/super_admin_dashboard.html"
    FOCUS_OPTIONS = {
        "all": {
            "label": "All signals",
            "description": "Full platform view across approvals, access, alerts, and operations.",
            "anchor": "",
        },
        "overdue_approvals": {
            "label": "Overdue approvals",
            "description": "Surface partner approvals that already crossed SLA and need intervention.",
            "anchor": "#approvals",
        },
        "blocked_accounts": {
            "label": "Blocked accounts",
            "description": "Jump directly into blocked or suspended access cases.",
            "anchor": "#access-watchlist",
        },
        "critical_alerts": {
            "label": "Critical alerts",
            "description": "Focus on warning and critical audit or system-alert signals first.",
            "anchor": "#security",
        },
    }
    NAV_ITEMS = [
        {"slug": "overview", "label": "Overview", "icon": "grid"},
        {"slug": "users", "label": "Users", "icon": "people"},
        {"slug": "doctors", "label": "Doctors", "icon": "clipboard2-pulse"},
        {"slug": "patients", "label": "Patients", "icon": "person-heart"},
        {"slug": "medicines", "label": "Medicines", "icon": "capsule-pill"},
        {"slug": "categories", "label": "Categories", "icon": "diagram-3"},
        {"slug": "inventory", "label": "Inventory", "icon": "box-seam"},
        {"slug": "orders", "label": "Orders", "icon": "bag-check"},
        {"slug": "prescriptions", "label": "Prescriptions", "icon": "file-earmark-medical"},
        {"slug": "appointments", "label": "Appointments", "icon": "calendar2-week"},
        {"slug": "analytics", "label": "Analytics", "icon": "graph-up-arrow"},
        {"slug": "payments", "label": "Payments", "icon": "credit-card-2-front"},
        {"slug": "notifications", "label": "Notifications", "icon": "bell"},
        {"slug": "roles-permissions", "label": "Permission Matrix", "icon": "shield-lock"},
        {"slug": "audit-logs", "label": "Audit Logs", "icon": "journal-text"},
        {"slug": "settings", "label": "Settings", "icon": "gear"},
    ]
    SECTION_DEFINITIONS = {
        "users": {
            "title": "Users",
            "subtitle": "Account growth, status health, and the latest registrations across the medicine platform.",
            "summary": "Monitor total user growth, active patient coverage, blocked states, and onboarding velocity.",
            "metric_keys": ["metrics", "platform_summary"],
            "table": "latest_users",
        },
        "doctors": {
            "title": "Doctors",
            "subtitle": "Doctor activity inferred from prescription flow and clinical submissions.",
            "summary": "Track doctor participation, recent prescription-linked doctors, and where medical review is active.",
            "metric_keys": ["prescription_snapshot"],
            "table": "recent_prescriptions",
        },
        "patients": {
            "title": "Patients",
            "subtitle": "Patient registration momentum and recent customer-side platform activity.",
            "summary": "Understand patient growth, recent customer registrations, and clinical/commerce demand touching patients.",
            "metric_keys": ["super_admin_kpis"],
            "table": "latest_users",
        },
        "medicines": {
            "title": "Medicines",
            "subtitle": "Medicine catalog coverage, low-stock risk, and operational medicine movement.",
            "summary": "See active medicine availability, low-stock alerts, and product-level operational movement.",
            "metric_keys": ["operations_snapshot"],
            "table": "top_inventory_risks",
        },
        "categories": {
            "title": "Categories",
            "subtitle": "Category structure and medicine mix across the current catalog.",
            "summary": "Review category distribution and catalog breadth for the healthcare commerce surface.",
            "metric_keys": ["platform_summary"],
            "table": "top_inventory_risks",
        },
        "inventory": {
            "title": "Inventory",
            "subtitle": "Warehouse and pharmacy inventory watch across stock pressure and movement.",
            "summary": "Prioritize low-stock items, movement flow, and inventory rows likely to impact fulfillment.",
            "metric_keys": ["operations_snapshot"],
            "table": "recent_movements",
        },
        "orders": {
            "title": "Orders",
            "subtitle": "Recent pharmacy orders, payment posture, and fulfillment-sensitive throughput.",
            "summary": "Watch commerce health from recent orders through payment and prescription dependencies.",
            "metric_keys": ["operations_snapshot", "financial_snapshot"],
            "table": "recent_orders",
        },
        "prescriptions": {
            "title": "Prescriptions",
            "subtitle": "Clinical intake, pharmacist pressure, and prescription review visibility.",
            "summary": "Focus on new prescriptions, urgent reviews, clarifications, and approval output.",
            "metric_keys": ["prescription_snapshot"],
            "table": "recent_prescriptions",
        },
        "appointments": {
            "title": "Appointments",
            "subtitle": "Appointment management surface ready for a dedicated scheduling module.",
            "summary": "This page is prepared for future appointment scheduling, care coordination, and doctor calendar workflows.",
            "metric_keys": [],
            "table": None,
            "empty_state": "No appointment module is wired yet. The navigation is now a real page and ready for appointment data when that module exists.",
        },
        "analytics": {
            "title": "Analytics",
            "subtitle": "Executive analytics for commerce, prescriptions, category mix, and patient growth.",
            "summary": "A focused analytics page for trend review without the density of the main overview screen.",
            "metric_keys": ["super_admin_kpis"],
            "table": None,
        },
        "payments": {
            "title": "Payments",
            "subtitle": "Payment attempts, failures, refunds, and webhook-level commerce health.",
            "summary": "Review gateway pressure, refund backlog, and payment reliability from one page.",
            "metric_keys": ["financial_snapshot"],
            "table": "recent_orders",
        },
        "notifications": {
            "title": "Notifications",
            "subtitle": "System alerts, inventory warnings, and operational messages that need attention.",
            "summary": "Use this page as the notification control surface for platform-wide alerts and staff-facing signals.",
            "metric_keys": ["security_snapshot"],
            "table": "system_alerts",
        },
        "roles-permissions": {
            "title": "Permission Matrix",
            "subtitle": "Manage module access across roles with an editable checkbox-based permission matrix.",
            "summary": "Control role access across catalog, prescriptions, orders, finance, support, security, and settings from one page.",
            "metric_keys": ["metrics"],
            "table": "staff_coverage",
        },
        "audit-logs": {
            "title": "Audit Logs",
            "subtitle": "Privileged events, control actions, and recent platform audit visibility.",
            "summary": "A dedicated audit page for security review, operator traceability, and compliance-friendly event history.",
            "metric_keys": ["security_snapshot"],
            "table": "recent_audit",
        },
        "settings": {
            "title": "Settings",
            "subtitle": "Platform controls, health endpoints, and administrative control shortcuts.",
            "summary": "Use this settings surface to access platform controls, readiness checks, and operations administration tools.",
            "metric_keys": ["platform_summary"],
            "table": "platform_controls",
        },
    }

    def build_super_admin_nav(self, active_slug: str) -> list[dict[str, str | bool]]:
        items: list[dict[str, str | bool]] = []
        for item in self.NAV_ITEMS:
            if item["slug"] == "overview":
                url = reverse("super-admin-dashboard")
            else:
                url = reverse("super-admin-section", kwargs={"section_slug": item["slug"]})
            items.append(
                {
                    "slug": item["slug"],
                    "label": item["label"],
                    "icon": item["icon"],
                    "url": url,
                    "active": item["slug"] == active_slug,
                }
            )
        return items

    def _focus_count_map(self, *, now):
        from platform_apps.audit.models import AuditLog

        last_24_hours = now - timezone.timedelta(hours=24)
        return {
            "all": None,
            "overdue_approvals": User.objects.filter(approval_status="pending", approval_due_at__lt=now).count(),
            "blocked_accounts": User.objects.filter(account_status__in=["blocked", "suspended"]).count(),
            "critical_alerts": AuditLog.objects.filter(severity__in=["warning", "critical"], created_at__gte=last_24_hours).count(),
        }

    @staticmethod
    def _trend_payload(*, current: int, previous: int) -> dict[str, str | int]:
        delta = current - previous
        if delta > 0:
            direction = "up"
            label = f"+{delta} vs prev 24h"
        elif delta < 0:
            direction = "down"
            label = f"{delta} vs prev 24h"
        else:
            direction = "flat"
            label = "No change vs prev 24h"
        return {
            "delta": delta,
            "direction": direction,
            "label": label,
        }

    def _set_dashboard_feedback(self, request, *, scope: str, level: str, message: str):
        request.session["super_admin_dashboard_feedback"] = {
            "scope": scope,
            "level": level,
            "message": message,
        }

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("dashboard_action") or "").strip()
        user_id = (request.POST.get("target_user_id") or "").strip()
        dashboard_note = (request.POST.get("dashboard_note") or "").strip()
        target_user = User.objects.filter(pk=user_id).first() if user_id else None

        if not action or target_user is None:
            self._set_dashboard_feedback(
                request,
                scope="global",
                level="danger",
                message="Invalid dashboard action.",
            )
            messages.error(request, "Invalid dashboard action.")
            return redirect("super-admin-dashboard")

        if action in {"approve_partner", "reject_partner"}:
            if target_user.role not in {"vendor", "pharmacist"} or target_user.approval_status != "pending":
                self._set_dashboard_feedback(
                    request,
                    scope="approvals",
                    level="danger",
                    message="That approval request is no longer available.",
                )
                messages.error(request, "That approval request is no longer available.")
                return redirect("super-admin-dashboard")
            if action == "approve_partner" and not target_user.documents_ready_for_approval:
                self._set_dashboard_feedback(
                    request,
                    scope="approvals",
                    level="danger",
                    message="Required proof documents must be verified before approval.",
                )
                messages.error(request, "Required proof documents must be verified before approval.")
                return redirect("super-admin-dashboard")
            if action == "reject_partner" and not dashboard_note:
                self._set_dashboard_feedback(
                    request,
                    scope="approvals",
                    level="danger",
                    message="Please add a reviewer note before rejecting an approval request.",
                )
                messages.error(request, "Please add a reviewer note before rejecting an approval request.")
                return redirect("super-admin-dashboard")

            previous_status = target_user.approval_status
            decision = "approved" if action == "approve_partner" else "rejected"
            target_user.approval_status = decision
            if dashboard_note:
                target_user.approval_notes = dashboard_note
            target_user.approval_reviewed_by = request.user
            target_user.approval_reviewed_at = timezone.now()
            target_user.save(update_fields=["approval_status", "approval_notes", "approval_reviewed_by", "approval_reviewed_at", "updated_at"])
            notify_user_of_approval_decision(target_user, previous_status=previous_status, actor=request.user)
            record_audit_event(
                actor=request.user,
                event_type="super_admin_dashboard_approval_action",
                entity_type="user",
                entity_id=target_user.pk,
                message=f"Super admin marked {target_user.email or target_user.phone_number} as {decision}.",
                meta={"role": target_user.role, "decision": decision, "dashboard_note": dashboard_note},
            )
            self._set_dashboard_feedback(
                request,
                scope="approvals",
                level="success",
                message=f"{target_user.email or target_user.phone_number} marked as {decision}.",
            )
            messages.success(request, f"{target_user.email or target_user.phone_number} marked as {decision}.")
            return redirect("super-admin-dashboard")

        if action in {"set_active", "set_blocked", "set_suspended"}:
            if target_user.pk == request.user.pk and action != "set_active":
                self._set_dashboard_feedback(
                    request,
                    scope="access",
                    level="danger",
                    message="You cannot block or suspend your own super admin account from the dashboard.",
                )
                messages.error(request, "You cannot block or suspend your own super admin account from the dashboard.")
                return redirect("super-admin-dashboard")

            new_status = {
                "set_active": "active",
                "set_blocked": "blocked",
                "set_suspended": "suspended",
            }[action]
            if new_status in {"blocked", "suspended"} and not dashboard_note:
                self._set_dashboard_feedback(
                    request,
                    scope="access",
                    level="danger",
                    message="Please provide a reason before blocking or suspending an account.",
                )
                messages.error(request, "Please provide a reason before blocking or suspending an account.")
                return redirect("super-admin-dashboard")
            previous_status = target_user.account_status
            target_user.account_status = new_status
            target_user.save(update_fields=["account_status", "is_active", "updated_at"])
            record_audit_event(
                actor=request.user,
                event_type="super_admin_dashboard_account_status_changed",
                entity_type="user",
                entity_id=target_user.pk,
                severity="warning" if new_status in {"blocked", "suspended"} else "info",
                message=(
                    f"Super admin changed account status for {target_user.email or target_user.phone_number} "
                    f"from {previous_status} to {new_status}."
                ),
                meta={
                    "previous_status": previous_status,
                    "new_status": new_status,
                    "role": target_user.role,
                    "dashboard_note": dashboard_note,
                },
            )
            self._set_dashboard_feedback(
                request,
                scope="access",
                level="success",
                message=f"{target_user.email or target_user.phone_number} is now {new_status}.",
            )
            messages.success(request, f"{target_user.email or target_user.phone_number} is now {new_status}.")
            return redirect("super-admin-dashboard")

        self._set_dashboard_feedback(
            request,
            scope="global",
            level="danger",
            message="Unsupported dashboard action.",
        )
        messages.error(request, "Unsupported dashboard action.")
        return redirect("super-admin-dashboard")

    def get_dashboard_metrics(self):
        by_role = User.objects.values("role").annotate(total=Count("id")).order_by("role")
        return [
            {"label": "Total Users", "value": User.objects.count()},
            {"label": "Blocked Users", "value": User.objects.filter(account_status="blocked").count()},
            {"label": "Suspended Users", "value": User.objects.filter(account_status="suspended").count()},
            {"label": "Pending Approvals", "value": User.objects.filter(approval_status="pending").count()},
            {"label": "Role Coverage", "value": len(list(by_role))},
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from platform_apps.audit.models import AuditLog
        from platform_apps.orders.models import PaymentAttempt, PaymentWebhookEvent, RefundRequest

        now = timezone.now()
        today = timezone.localdate()
        last_24_hours = now - timezone.timedelta(hours=24)
        previous_24_hours = last_24_hours - timezone.timedelta(hours=24)
        dashboard_focus = (self.request.GET.get("focus") or "all").strip()
        if dashboard_focus not in self.FOCUS_OPTIONS:
            dashboard_focus = "all"
        focus_counts = self._focus_count_map(now=now)
        by_role = list(User.objects.values("role").annotate(total=Count("id")).order_by("role"))
        recent_audit = AuditLog.objects.select_related("actor").order_by("-created_at")[:8]
        critical_audit = AuditLog.objects.select_related("actor").filter(severity__in=["warning", "critical"]).order_by("-created_at")[:6]
        pending_approvals_queryset = User.objects.filter(approval_status="pending").select_related("approval_assigned_to")
        if dashboard_focus == "overdue_approvals":
            pending_approvals_queryset = pending_approvals_queryset.filter(approval_due_at__lt=now)
        pending_approvals = list(pending_approvals_queryset.order_by("approval_due_at", "-created_at")[:6])
        for pending_user in pending_approvals:
            pending_user.dashboard_is_overdue = bool(pending_user.approval_due_at and pending_user.approval_due_at < now)
        latest_users = User.objects.order_by("-created_at")[:6]
        recent_orders = Order.objects.select_related("user").order_by("-created_at")[:6]
        recent_prescriptions = Prescription.objects.select_related("user", "reviewed_by").order_by("-created_at")[:6]
        recent_movements = StockMovement.objects.select_related("product", "location", "created_by").order_by("-created_at")[:6]
        total_revenue = Order.objects.aggregate(total=Sum("total")).get("total") or 0
        reviewer_rows = list(
            User.objects.filter(role__in=["admin", "super_admin"], account_status="active")
            .annotate(
                assigned_total=Count("assigned_user_approvals", distinct=True),
                pending_assigned_total=Count(
                    "assigned_user_approvals",
                    filter=Q(assigned_user_approvals__approval_status="pending"),
                    distinct=True,
                ),
                overdue_assigned_total=Count(
                    "assigned_user_approvals",
                    filter=Q(
                        assigned_user_approvals__approval_status="pending",
                        assigned_user_approvals__approval_due_at__lt=now,
                    ),
                    distinct=True,
                ),
            )
            .order_by("role", "full_name", "phone_number")
        )
        for reviewer in reviewer_rows:
            if not reviewer.approval_available_for_assignment:
                reviewer.reviewer_status_label = "Manual hold"
            elif reviewer.approval_unavailable_until and reviewer.approval_unavailable_until > now:
                reviewer.reviewer_status_label = "Unavailable"
            elif not reviewer.is_within_approval_shift():
                reviewer.reviewer_status_label = "Off shift"
            else:
                reviewer.reviewer_status_label = "Available"

        rejected_document_count = User.objects.filter(
            approval_status="pending",
        ).filter(
            Q(role="vendor", vendor_license_document_status="rejected")
            | Q(role="pharmacist", pharmacist_registration_document_status="rejected")
        ).count()
        access_watchlist_queryset = User.objects.filter(account_status__in=["blocked", "suspended"])
        if dashboard_focus == "blocked_accounts":
            access_watchlist_queryset = access_watchlist_queryset.order_by("-updated_at")
        system_alerts_queryset = Notification.objects.filter(kind__in=["system_alert", "inventory_alert"], is_read=False)
        if dashboard_focus == "critical_alerts":
            system_alerts_queryset = system_alerts_queryset.filter(kind="system_alert")

        recent_days = [today - timezone.timedelta(days=offset) for offset in range(6, -1, -1)]
        chart_labels = [day.strftime("%d %b") for day in recent_days]
        revenue_series = []
        orders_series = []
        prescriptions_series = []
        patient_growth_series = []
        for day in recent_days:
            revenue_total = (
                Order.objects.filter(created_at__date=day).aggregate(total=Sum("total")).get("total") or 0
            )
            revenue_series.append(float(revenue_total))
            orders_series.append(Order.objects.filter(created_at__date=day).count())
            prescriptions_series.append(Prescription.objects.filter(created_at__date=day).count())
            patient_growth_series.append(User.objects.filter(role="customer", created_at__date=day).count())

        category_distribution = list(
            Category.objects.filter(is_active=True)
            .annotate(product_total=Count("products", filter=Q(products__is_active=True)))
            .order_by("-product_total", "name")[:5]
        )
        category_labels = [item.name for item in category_distribution]
        category_values = [item.product_total for item in category_distribution]

        ai_brief = []
        if User.objects.filter(approval_status="pending", approval_due_at__lt=now).count():
            ai_brief.append("Approval SLA pressure is rising and needs immediate reviewer attention.")
        if Order.objects.filter(status="pending_prescription_review").count():
            ai_brief.append("Prescription-linked orders are a visible drag on fulfillment throughput.")
        if InventoryItem.objects.filter(quantity_on_hand__lte=10).count():
            ai_brief.append("Inventory risk is emerging in low-stock rows and should be reviewed before demand spikes.")
        if not ai_brief:
            ai_brief.append("Platform pressure is stable across approvals, operations, and access control.")

        health_checks = [
            {"label": "Live check", "url": "/api/v1/health/live/"},
            {"label": "Ready check", "url": "/api/v1/health/ready/"},
            {"label": "Metrics", "url": "/api/v1/health/metrics/"},
            {"label": "Prometheus", "url": "/api/v1/health/metrics.prom"},
        ]
        focus_tabs = []
        for key, config in self.FOCUS_OPTIONS.items():
            href = self.request.path
            if key != "all":
                href = f"{href}?focus={key}{config['anchor']}"
            elif config["anchor"]:
                href = f"{href}{config['anchor']}"
            focus_tabs.append(
                {
                    "key": key,
                    "label": config["label"],
                    "count": focus_counts.get(key),
                    "href": href,
                    "active": key == dashboard_focus,
                }
            )

        active_patients = User.objects.filter(role="customer", account_status="active").count()
        registered_doctors = (
            Prescription.objects.exclude(doctor_name__exact="")
            .values("doctor_name")
            .distinct()
            .count()
        )
        low_stock_alerts = InventoryItem.objects.filter(quantity_on_hand__lte=10).count()
        expiring_medicines = []
        date_range_options = [
            {"label": "Last 7 days", "value": "7d"},
            {"label": "Last 30 days", "value": "30d"},
            {"label": "Quarter", "value": "90d"},
        ]

        context.update(
            {
                "quick_actions": [
                    {"label": "Approval queue", "url": "/admin/approval-queue/", "icon": "clipboard-check"},
                    {"label": "Reviewer schedules", "url": "/admin/reviewer-schedules/", "icon": "calendar3"},
                    {"label": "Admin live feed", "url": "/admin/live/", "icon": "activity"},
                    {"label": "Django admin", "url": "/admin/", "icon": "gear"},
                    {"label": "Health endpoints", "url": "/api/v1/health/live/", "icon": "heart-pulse"},
                ],
                "role_breakdown": by_role,
                "recent_audit": recent_audit,
                "critical_audit": critical_audit,
                "pending_approvals": pending_approvals,
                "health_checks": health_checks,
                "platform_summary": [
                    {"label": "Orders", "value": Order.objects.count()},
                    {"label": "Prescriptions", "value": Prescription.objects.count()},
                    {"label": "Products", "value": Product.objects.filter(is_active=True).count()},
                    {"label": "Unread notifications", "value": Notification.objects.filter(is_read=False).count()},
                ],
                "approval_snapshot": [
                    {"label": "Pending approvals", "value": User.objects.filter(approval_status="pending").count(), "hint": "Accounts still waiting for a decision."},
                    {"label": "Overdue approvals", "value": User.objects.filter(approval_status="pending", approval_due_at__lt=now).count(), "hint": "Requests that crossed SLA."},
                    {"label": "Unassigned approvals", "value": User.objects.filter(approval_status="pending", approval_assigned_to__isnull=True).count(), "hint": "Needs an owner immediately."},
                    {"label": "Rejected documents", "value": rejected_document_count, "hint": "Proof files blocked in review."},
                ],
                "security_snapshot": [
                    {"label": "Failed logins 24h", "value": AuditLog.objects.filter(event_type="portal_login_failed", created_at__gte=last_24_hours).count(), "hint": "Authentication failures across the portal."},
                    {"label": "Critical audit 24h", "value": AuditLog.objects.filter(severity="critical", created_at__gte=last_24_hours).count(), "hint": "Highest-risk privileged events."},
                    {"label": "Blocked + suspended", "value": User.objects.filter(account_status__in=["blocked", "suspended"]).count(), "hint": "Accounts not allowed to sign in."},
                    {"label": "Unread system alerts", "value": Notification.objects.filter(kind="system_alert", is_read=False).count(), "hint": "Operational signals still unacknowledged."},
                ],
                "operations_snapshot": [
                    {"label": "Pending Rx orders", "value": Order.objects.filter(status="pending_prescription_review").count(), "hint": "Orders waiting on clinical review."},
                    {"label": "Payment pending", "value": Order.objects.filter(payment_status__in=["pending", "cod_pending"]).count(), "hint": "Checkout sessions not fully settled."},
                    {"label": "Open refunds", "value": RefundRequest.objects.filter(status__in=["requested", "approved"]).count(), "hint": "Refund work still unresolved."},
                    {"label": "Low stock rows", "value": InventoryItem.objects.filter(quantity_on_hand__lte=10).count(), "hint": "Inventory positions nearing risk."},
                ],
                "prescription_snapshot": [
                    {"label": "Pending review", "value": Prescription.objects.filter(status="pending_review").count(), "hint": "Waiting for pharmacist action."},
                    {"label": "Urgent queue", "value": Prescription.objects.filter(status="pending_review", review_priority="urgent").count(), "hint": "Most time-sensitive clinical work."},
                    {"label": "Clarifications", "value": Prescription.objects.filter(status="clarification_required").count(), "hint": "Customer follow-up still needed."},
                    {"label": "Approved today", "value": Prescription.objects.filter(status="approved", updated_at__date=today).count(), "hint": "Clinical throughput since midnight."},
                ],
                "financial_snapshot": [
                    {"label": "Payment attempts pending", "value": PaymentAttempt.objects.filter(status__in=["created", "pending"]).count(), "hint": "Gateway sessions not yet settled."},
                    {"label": "Payment failures 24h", "value": PaymentAttempt.objects.filter(status="failed", initiated_at__gte=last_24_hours).count(), "hint": "Checkout attempts that failed recently."},
                    {"label": "Refund requests", "value": RefundRequest.objects.count(), "hint": "Total refund cases in the system."},
                    {"label": "Duplicate webhooks", "value": PaymentWebhookEvent.objects.filter(was_duplicate=True).count(), "hint": "Potential provider noise or replay traffic."},
                ],
                "staff_coverage": reviewer_rows,
                "system_alerts": system_alerts_queryset.order_by("-created_at")[:6],
                "top_inventory_risks": InventoryItem.objects.select_related("product", "location").order_by("quantity_on_hand", "-updated_at")[:6],
                "access_watchlist": access_watchlist_queryset.order_by("-updated_at")[:6],
                "recent_control_actions": AuditLog.objects.select_related("actor")
                .filter(
                    event_type__in=[
                        "super_admin_dashboard_approval_action",
                        "super_admin_dashboard_account_status_changed",
                    ]
                )
                .order_by("-created_at")[:8],
                "platform_controls": [
                    {"label": "Approval queue", "url": "/admin/approval-queue/", "text": "Clear pending vendor and pharmacist onboarding."},
                    {"label": "Reviewer schedules", "url": "/admin/reviewer-schedules/", "text": "Adjust reviewer availability, shifts, and leave."},
                    {"label": "Live ops feed", "url": "/admin/live/", "text": "Watch incoming operational events as they happen."},
                    {"label": "Health checks", "url": "/api/v1/health/ready/", "text": "Confirm readiness before pushing operational changes."},
                ],
                "critical_now": [
                    {
                        "label": "Overdue approvals",
                        "value": User.objects.filter(approval_status="pending", approval_due_at__lt=now).count(),
                        "href": "/super-admin/dashboard/?focus=overdue_approvals#approvals",
                        "tone": "danger",
                        "trend": self._trend_payload(
                            current=User.objects.filter(approval_status="pending", approval_due_at__lt=now).count(),
                            previous=User.objects.filter(
                                approval_status="pending",
                                approval_due_at__gte=previous_24_hours,
                                approval_due_at__lt=last_24_hours,
                            ).count(),
                        ),
                    },
                    {
                        "label": "Blocked or suspended",
                        "value": User.objects.filter(account_status__in=["blocked", "suspended"]).count(),
                        "href": "/super-admin/dashboard/?focus=blocked_accounts#access-watchlist",
                        "tone": "danger",
                        "trend": self._trend_payload(
                            current=User.objects.filter(account_status__in=["blocked", "suspended"]).count(),
                            previous=User.objects.filter(
                                account_status__in=["blocked", "suspended"],
                                updated_at__gte=previous_24_hours,
                                updated_at__lt=last_24_hours,
                            ).count(),
                        ),
                    },
                    {
                        "label": "Critical audit 24h",
                        "value": AuditLog.objects.filter(severity="critical", created_at__gte=last_24_hours).count(),
                        "href": "/super-admin/dashboard/?focus=critical_alerts#security",
                        "tone": "warning",
                        "trend": self._trend_payload(
                            current=AuditLog.objects.filter(severity="critical", created_at__gte=last_24_hours).count(),
                            previous=AuditLog.objects.filter(
                                severity="critical",
                                created_at__gte=previous_24_hours,
                                created_at__lt=last_24_hours,
                            ).count(),
                        ),
                    },
                    {
                        "label": "Unread system alerts",
                        "value": Notification.objects.filter(kind="system_alert", is_read=False).count(),
                        "href": "/super-admin/dashboard/?focus=critical_alerts#security",
                        "tone": "warning",
                        "trend": self._trend_payload(
                            current=Notification.objects.filter(kind="system_alert", is_read=False).count(),
                            previous=Notification.objects.filter(
                                kind="system_alert",
                                created_at__gte=previous_24_hours,
                                created_at__lt=last_24_hours,
                            ).count(),
                        ),
                    },
                ],
                "dashboard_feedback": self.request.session.pop("super_admin_dashboard_feedback", None),
                "dashboard_focus": dashboard_focus,
                "dashboard_focus_tabs": focus_tabs,
                "dashboard_focus_config": self.FOCUS_OPTIONS[dashboard_focus],
                "dashboard_last_refreshed_at": timezone.localtime(now),
                "latest_users": latest_users,
                "recent_orders": recent_orders,
                "recent_prescriptions": recent_prescriptions,
                "recent_movements": recent_movements,
                "ai_brief": ai_brief,
                "nav_notifications_count": system_alerts_queryset.count(),
                "nav_messages_count": AuditLog.objects.filter(
                    event_type__in=[
                        "super_admin_dashboard_approval_action",
                        "super_admin_dashboard_account_status_changed",
                    ]
                ).count(),
                "dashboard_chart_data": {
                    "labels": chart_labels,
                    "revenue": revenue_series,
                    "orders": orders_series,
                    "prescriptions": prescriptions_series,
                    "patients": patient_growth_series,
                    "categories": {
                        "labels": category_labels,
                        "values": category_values,
                    },
                },
                "total_revenue": total_revenue,
                "super_admin_kpis": [
                    {
                        "label": "Total Revenue",
                        "value": total_revenue,
                        "display": f"₹{total_revenue}",
                        "icon": "currency-rupee",
                        "trend_label": "+12.8% month on month",
                        "trend_tone": "positive",
                        "subtext": "Gross platform commerce processed through the medicine network.",
                        "progress": 82,
                    },
                    {
                        "label": "Total Orders",
                        "value": Order.objects.count(),
                        "display": str(Order.objects.count()),
                        "icon": "bag-check",
                        "trend_label": f"{Order.objects.filter(created_at__gte=last_24_hours).count()} in last 24h",
                        "trend_tone": "neutral",
                        "subtext": "End-to-end pharmacy orders across the commerce layer.",
                        "progress": 74,
                    },
                    {
                        "label": "Total Medicines",
                        "value": Product.objects.filter(is_active=True).count(),
                        "display": str(Product.objects.filter(is_active=True).count()),
                        "icon": "capsule-pill",
                        "trend_label": f"{Category.objects.filter(is_active=True).count()} active categories",
                        "trend_tone": "positive",
                        "subtext": "Live medicine catalog currently available to operations.",
                        "progress": 68,
                    },
                    {
                        "label": "Active Patients",
                        "value": active_patients,
                        "display": str(active_patients),
                        "icon": "person-heart",
                        "trend_label": f"{sum(patient_growth_series)} new this week",
                        "trend_tone": "positive",
                        "subtext": "Patients actively represented in the platform account base.",
                        "progress": 71,
                    },
                    {
                        "label": "Registered Doctors",
                        "value": registered_doctors,
                        "display": str(registered_doctors),
                        "icon": "clipboard2-pulse",
                        "trend_label": "Derived from prescription doctor records",
                        "trend_tone": "neutral",
                        "subtext": "Distinct doctors referenced through prescription activity.",
                        "progress": 58,
                    },
                    {
                        "label": "Low Stock Alerts",
                        "value": low_stock_alerts,
                        "display": str(low_stock_alerts),
                        "icon": "exclamation-triangle",
                        "trend_label": "Immediate inventory watchlist",
                        "trend_tone": "warning",
                        "subtext": "Inventory rows that need replenishment or manual attention.",
                        "progress": min(low_stock_alerts * 8, 100),
                    },
                ],
                "date_range_options": date_range_options,
                "selected_date_range": "7d",
                "expiring_medicines": expiring_medicines,
                "super_admin_nav": self.build_super_admin_nav("overview"),
            }
        )
        return context


class SuperAdminSectionView(SuperAdminDashboardView):
    template_name = "dashboards/super_admin_section.html"
    USER_ROWS_PER_PAGE_CHOICES = (10, 25, 50, 100)
    ROLE_CATALOG = get_role_catalog_payload()
    USER_SORT_FIELDS = {
        "id": "id",
        "-id": "-id",
        "employee_code": "employee_code",
        "-employee_code": "-employee_code",
        "full_name": "full_name",
        "-full_name": "-full_name",
        "username": "username",
        "-username": "-username",
        "role": "role",
        "-role": "-role",
        "department": "department",
        "-department": "-department",
        "designation": "designation",
        "-designation": "-designation",
        "email": "email",
        "-email": "-email",
        "phone_number": "phone_number",
        "-phone_number": "-phone_number",
        "country": "country",
        "-country": "-country",
        "state": "state",
        "-state": "-state",
        "district": "district",
        "-district": "-district",
        "account_status": "account_status",
        "-account_status": "-account_status",
        "email_verified": "email_verified",
        "-email_verified": "-email_verified",
        "account_locked": "account_locked",
        "-account_locked": "-account_locked",
        "customer_active_hrs": "customer_active_seconds_total",
        "-customer_active_hrs": "-customer_active_seconds_total",
        "last_login": "last_login",
        "-last_login": "-last_login",
        "created_at": "created_at",
        "-created_at": "-created_at",
        "updated_at": "updated_at",
        "-updated_at": "-updated_at",
    }
    USER_COLUMNS = (
        {"key": "id", "label": "User ID", "default": True},
        {"key": "employee_code", "label": "Employee Code", "default": True},
        {"key": "full_name", "label": "Full Name", "default": True},
        {"key": "username", "label": "Username", "default": True},
        {"key": "type_of_user", "label": "Type of User", "default": True},
        {"key": "role", "label": "Role", "default": True},
        {"key": "department", "label": "Department", "default": True},
        {"key": "designation", "label": "Designation", "default": True},
        {"key": "email", "label": "Email ID", "default": True},
        {"key": "phone_number", "label": "Mobile Number", "default": True},
        {"key": "country", "label": "Country", "default": True},
        {"key": "state", "label": "State", "default": True},
        {"key": "district", "label": "District", "default": True},
        {"key": "address", "label": "Address", "default": True},
        {"key": "customer_active_hrs", "label": "Customer Active Hrs in Website", "default": True},
        {"key": "account_status", "label": "Status", "default": True},
        {"key": "email_verified", "label": "Email Verified", "default": True},
        {"key": "account_locked", "label": "Account Locked", "default": True},
        {"key": "mfa_enabled", "label": "MFA Enabled", "default": False},
        {"key": "failed_login_attempts", "label": "Failed Attempts", "default": False},
        {"key": "last_login", "label": "Last Login", "default": True},
        {"key": "last_login_ip", "label": "Last Login IP", "default": True},
        {"key": "password_last_changed_at", "label": "Password Last Changed", "default": False},
        {"key": "created_at", "label": "Created On", "default": True},
        {"key": "created_by", "label": "Created By", "default": True},
        {"key": "updated_at", "label": "Updated On", "default": True},
        {"key": "updated_by", "label": "Updated By", "default": True},
        {"key": "remarks", "label": "Remarks", "default": True},
    )

    def _user_permissions(self) -> dict[str, bool]:
        from .views import resolve_user_permissions

        return resolve_user_permissions(self.request.user)

    def _user_base_queryset(self):
        return (
            User.objects.select_related("created_by", "updated_by", "deleted_by")
            .prefetch_related("addresses")
            .order_by("-created_at")
        )

    def _get_user_filters(self):
        request = self.request
        rows = request.GET.get("rows", "25")
        try:
            rows = int(rows)
        except (TypeError, ValueError):
            rows = 25
        if rows not in self.USER_ROWS_PER_PAGE_CHOICES:
            rows = 25

        sort = request.GET.get("sort", "-created_at")
        if sort not in self.USER_SORT_FIELDS:
            sort = "-created_at"

        default_columns = [column["key"] for column in self.USER_COLUMNS if column["default"]]
        requested_columns = request.GET.getlist("columns")
        if "columns_configured" in request.GET:
            visible_columns = [column["key"] for column in self.USER_COLUMNS if column["key"] in requested_columns]
        else:
            visible_columns = [column["key"] for column in self.USER_COLUMNS if column["key"] in requested_columns] or default_columns

        return {
            "q": (request.GET.get("q") or "").strip(),
            "type_of_user": (request.GET.get("type_of_user") or "").strip(),
            "role": (request.GET.get("role") or "").strip(),
            "department": (request.GET.get("department") or "").strip(),
            "designation": (request.GET.get("designation") or "").strip(),
            "status": (request.GET.get("status") or "").strip(),
            "country": (request.GET.get("country") or "").strip(),
            "state": (request.GET.get("state") or "").strip(),
            "email_verified": (request.GET.get("email_verified") or "").strip(),
            "account_locked": (request.GET.get("account_locked") or "").strip(),
            "active_min_minutes": (request.GET.get("active_min_minutes") or "").strip(),
            "active_max_minutes": (request.GET.get("active_max_minutes") or "").strip(),
            "created_from": (request.GET.get("created_from") or "").strip(),
            "created_to": (request.GET.get("created_to") or "").strip(),
            "last_login_from": (request.GET.get("last_login_from") or "").strip(),
            "last_login_to": (request.GET.get("last_login_to") or "").strip(),
            "rows": rows,
            "sort": sort,
            "page": request.GET.get("page") or "1",
            "visible_columns": visible_columns,
        }

    @staticmethod
    def _parse_date(value: str):
        if not value:
            return None
        try:
            return timezone.datetime.fromisoformat(value).date()
        except ValueError:
            return None

    @staticmethod
    def _safe_int_string(value: str) -> str:
        value = (value or "").strip()
        return value if value.isdigit() else ""

    def _apply_user_filters(self, queryset, filters):
        query = filters["q"]
        if query:
            query_filter = (
                Q(employee_code__icontains=query)
                | Q(full_name__icontains=query)
                | Q(username__icontains=query)
                | Q(email__icontains=query)
                | Q(phone_number__icontains=query)
                | Q(role__icontains=query)
                | Q(department__icontains=query)
                | Q(designation__icontains=query)
                | Q(country__icontains=query)
                | Q(state__icontains=query)
                | Q(district__icontains=query)
                | Q(account_status__icontains=query)
            )
            if query.isdigit():
                query_filter |= Q(pk=int(query))
            queryset = queryset.filter(query_filter)

        for field_name in ("type_of_user", "role", "department", "designation", "country", "state"):
            value = filters[field_name]
            if value:
                queryset = queryset.filter(**{field_name: value})
        if filters["status"]:
            queryset = queryset.filter(account_status=filters["status"])
        if filters["email_verified"] in {"true", "false"}:
            queryset = queryset.filter(email_verified=filters["email_verified"] == "true")
        if filters["account_locked"] in {"true", "false"}:
            queryset = queryset.filter(account_locked=filters["account_locked"] == "true")
        try:
            active_min_minutes = int(filters["active_min_minutes"])
        except (TypeError, ValueError):
            active_min_minutes = None
        try:
            active_max_minutes = int(filters["active_max_minutes"])
        except (TypeError, ValueError):
            active_max_minutes = None
        if active_min_minutes is not None and active_min_minutes >= 0:
            queryset = queryset.filter(customer_active_seconds_total__gte=active_min_minutes * 60)
        if active_max_minutes is not None and active_max_minutes >= 0:
            queryset = queryset.filter(customer_active_seconds_total__lte=active_max_minutes * 60)

        created_from = self._parse_date(filters["created_from"])
        created_to = self._parse_date(filters["created_to"])
        login_from = self._parse_date(filters["last_login_from"])
        login_to = self._parse_date(filters["last_login_to"])
        if created_from:
            queryset = queryset.filter(created_at__date__gte=created_from)
        if created_to:
            queryset = queryset.filter(created_at__date__lte=created_to)
        if login_from:
            queryset = queryset.filter(last_login__date__gte=login_from)
        if login_to:
            queryset = queryset.filter(last_login__date__lte=login_to)

        return queryset.order_by(self.USER_SORT_FIELDS[filters["sort"]]).distinct()

    def _user_metric_cards(self):
        today = timezone.localdate()
        now = timezone.now()
        month_start = today.replace(day=1)
        return [
            {"label": "Total Users", "value": User.objects.count(), "hint": "All user records across portal access."},
            {"label": "Active Users", "value": User.objects.filter(account_status="active").count(), "hint": "Accounts allowed to sign in now."},
            {"label": "Inactive Users", "value": User.objects.filter(account_status="inactive").count(), "hint": "Accounts disabled without a block state."},
            {"label": "Blocked Users", "value": User.objects.filter(account_status="blocked").count(), "hint": "Security-blocked identities."},
            {"label": "Locked Accounts", "value": User.objects.filter(account_locked=True).count(), "hint": "Accounts locked after control actions or failures."},
            {"label": "New Users This Month", "value": User.objects.filter(created_at__date__gte=month_start).count(), "hint": "Fresh registrations since month start."},
            {"label": "Users Logged In Today", "value": User.objects.filter(last_login__date=today).count(), "hint": "Accounts with live usage today."},
            {"label": "Pending Email Verification", "value": User.objects.filter(email_verified=False, deleted_at__isnull=True).count(), "hint": "Accounts awaiting verified email state."},
        ]

    def _user_filter_options(self, queryset):
        return {
            "roles": sorted(set(queryset.values_list("role", flat=True))),
            "departments": sorted({value for value in queryset.values_list("department", flat=True) if value}),
            "designations": sorted({value for value in queryset.values_list("designation", flat=True) if value}),
            "countries": sorted({value for value in queryset.values_list("country", flat=True) if value}),
            "states": sorted({value for value in queryset.values_list("state", flat=True) if value}),
            "type_of_users": User.TYPE_OF_USER_CHOICES,
            "statuses": User.ACCOUNT_STATUS_CHOICES,
        }

    @staticmethod
    def _attach_customer_activity_windows(users):
        users = list(users)
        if not users:
            return users
        today = timezone.localdate()
        week_start = today - timezone.timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        user_ids = [user.pk for user in users]
        rows = (
            CustomerWebsiteActivityDaily.objects.filter(user_id__in=user_ids, activity_date__gte=month_start)
            .values("user_id")
            .annotate(
                month_seconds=Sum("active_seconds"),
                week_seconds=Sum("active_seconds", filter=Q(activity_date__gte=week_start)),
                today_seconds=Sum("active_seconds", filter=Q(activity_date=today)),
            )
        )
        activity_by_user = {row["user_id"]: row for row in rows}
        for user in users:
            row = activity_by_user.get(user.pk, {})
            user.customer_active_seconds_today = row.get("today_seconds") or 0
            user.customer_active_seconds_week = row.get("week_seconds") or 0
            user.customer_active_seconds_month = row.get("month_seconds") or 0
        return users

    def _user_querystring(self, filters, *, overrides=None, remove=None):
        overrides = overrides or {}
        remove = set(remove or [])
        query = []
        for key, value in filters.items():
            if key in {"visible_columns"}:
                continue
            if key in remove:
                continue
            if value in {"", None}:
                continue
            query.append((key, value))
        for value in filters["visible_columns"]:
            if "columns" not in remove:
                query.append(("columns", value))
        for key, value in overrides.items():
            if value in {"", None}:
                continue
            if isinstance(value, list):
                for item in value:
                    query.append((key, item))
            else:
                query.append((key, value))
        encoded = urlencode(query, doseq=True)
        return f"?{encoded}" if encoded else ""

    def _export_users_csv(self, queryset, *, selected_only=False):
        users = self._attach_customer_activity_windows(queryset)
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="user-management-export.csv"'
        writer = csv.writer(response)
        writer.writerow(
            [
                "S.No",
                "User ID",
                "Employee Code",
                "Full Name",
                "Username",
                "Type of User",
                "Role",
                "Department",
                "Designation",
                "Email",
                "Mobile",
                "Country",
                "State",
                "District",
                "Address",
                "Customer Active Hrs in Website",
                "Customer Active Today",
                "Customer Active This Week",
                "Customer Active This Month",
                "Status",
                "Email Verified",
                "Account Locked",
                "MFA Enabled",
                "Failed Login Attempts",
                "Last Login",
                "Last Login IP",
                "Created On",
                "Created By",
                "Updated On",
                "Updated By",
                "Remarks",
            ]
        )
        for index, user in enumerate(users, start=1):
            writer.writerow(
                [
                    index,
                    user.pk,
                    user.employee_code or "",
                    user.full_name or "",
                    user.username or "",
                    user.get_type_of_user_display(),
                    user.get_role_display(),
                    user.department or "",
                    user.designation or "",
                    user.email or "",
                    user.phone_number or "",
                    user.country or "",
                    user.state or "",
                    user.district or "",
                    user.address or "",
                    user.customer_active_duration_label,
                    format_active_duration(getattr(user, "customer_active_seconds_today", 0)),
                    format_active_duration(getattr(user, "customer_active_seconds_week", 0)),
                    format_active_duration(getattr(user, "customer_active_seconds_month", 0)),
                    user.get_account_status_display(),
                    "Yes" if user.email_verified else "No",
                    "Yes" if user.account_locked else "No",
                    "Yes" if user.mfa_enabled else "No",
                    user.failed_login_attempts,
                    timezone.localtime(user.last_login).strftime("%d %b %Y, %H:%M") if user.last_login else "",
                    user.last_login_ip or "",
                    timezone.localtime(user.created_at).strftime("%d %b %Y, %H:%M"),
                    user.created_by.full_name if user.created_by else "",
                    timezone.localtime(user.updated_at).strftime("%d %b %Y, %H:%M"),
                    user.updated_by.full_name if user.updated_by else "",
                    user.remarks or "",
                ]
            )
        record_audit_event(
            actor=self.request.user,
            event_type="user_exported",
            entity_type="user",
            message="User management export downloaded.",
            meta={"selected_only": selected_only, "count": len(users)},
        )
        return response

    def _apply_user_state_change(self, target_user: User, *, new_status: str | None = None, locked: bool | None = None, action_label: str):
        if target_user.pk == self.request.user.pk and action_label in {"delete", "lock", "deactivate", "block", "suspend"}:
            messages.error(self.request, "You cannot apply that action to your own super admin account.")
            return
        previous = {
            "status": target_user.account_status,
            "locked": target_user.account_locked,
            "failed_login_attempts": target_user.failed_login_attempts,
        }
        if new_status:
            target_user.account_status = new_status
        if locked is not None:
            target_user.account_locked = locked
        target_user.updated_by = self.request.user
        if action_label == "delete":
            target_user.deleted_at = timezone.now()
            target_user.deleted_by = self.request.user
            target_user.account_status = "deleted"
        elif new_status and new_status != "deleted":
            target_user.deleted_at = None
            target_user.deleted_by = None
        target_user.save(update_fields=[
            "account_status",
            "account_locked",
            "is_active",
            "updated_at",
            "updated_by",
            "deleted_at",
            "deleted_by",
        ])
        record_audit_event(
            actor=self.request.user,
            event_type=f"user_{action_label}",
            entity_type="user",
            entity_id=target_user.pk,
            severity="warning" if action_label in {"delete", "lock", "block", "suspend"} else "info",
            message=f"{action_label.replace('_', ' ').title()} action executed for {target_user.full_name or target_user.phone_number}.",
            meta={"old_value": previous, "new_value": {"status": target_user.account_status, "locked": target_user.account_locked}},
        )

    def get(self, request, *args, **kwargs):
        section_slug = (kwargs.get("section_slug") or "").strip()
        if section_slug == "users":
            filters = self._get_user_filters()
            if request.GET.get("save_view") == "1":
                saved_filters = dict(filters)
                saved_filters["page"] = "1"
                view_name = (request.GET.get("save_view_name") or "").strip() or f"Saved View {timezone.localtime().strftime('%d %b %H:%M')}"
                saved_view, _ = UserSavedFilterView.objects.update_or_create(
                    owner=request.user,
                    name=view_name,
                    defaults={"filters": saved_filters},
                )
                request.session["super_admin_users_saved_view"] = saved_filters
                messages.success(request, f"Filter view '{saved_view.name}' saved.")
                return redirect(f"{request.path}{self._user_querystring(filters, remove=['page', 'save_view', 'save_view_name'])}")
            if request.GET.get("apply_saved_view") == "1":
                saved_view = None
                saved_view_id = self._safe_int_string(request.GET.get("saved_view_id") or "")
                if saved_view_id:
                    saved_view = UserSavedFilterView.objects.filter(owner=request.user, pk=saved_view_id).first()
                if saved_view:
                    return redirect(f"{request.path}{self._user_querystring(saved_view.filters, remove=['page'])}")
                saved_filters = request.session.get("super_admin_users_saved_view")
                if saved_filters:
                    return redirect(f"{request.path}{self._user_querystring(saved_filters, remove=['page'])}")
                messages.error(request, "No saved filter view is available yet.")
                return redirect("super-admin-section", section_slug="users")
            if request.GET.get("export") in {"csv", "xls"} and self._user_permissions()["export"]:
                users_queryset = self._apply_user_filters(self._user_base_queryset(), filters)
                if request.GET.get("export") == "xls":
                    from .views import _export_users_excel_xml

                    return _export_users_excel_xml(users_queryset)
                return self._export_users_csv(users_queryset)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        section_slug = (kwargs.get("section_slug") or "").strip()
        if section_slug == "roles-permissions":
            from .views import (
                PERMISSION_MATRIX_SECTIONS,
                ensure_role_permission_matrices,
                normalize_permission_matrix_states,
                permission_state_from_flags,
                sync_user_permission_fields_from_matrix,
            )

            if (request.POST.get("permission_action") or "").strip() != "save":
                messages.error(request, "Unsupported permission matrix action.")
                return redirect("super-admin-section", section_slug=section_slug)

            wants_json = (
                request.headers.get("X-Requested-With") == "XMLHttpRequest"
                or "application/json" in request.headers.get("Accept", "")
            )

            ensure_role_permission_matrices()
            matrices = {matrix.role: matrix for matrix in RolePermissionMatrix.objects.all()}
            for role, _label in User.ROLE_CHOICES:
                matrix = matrices[role]
                matrix_states = normalize_permission_matrix_states(role, matrix.matrix_permissions)
                for section in PERMISSION_MATRIX_SECTIONS:
                    for action in section["actions"]:
                        state_name = f"matrix_state__{role}__{section['key']}__{action['key']}"
                        access_name = f"perm__{role}__{section['key']}__{action['key']}"
                        scope_name = f"scope__{role}__{section['key']}__{action['key']}"
                        selected_state = (request.POST.get(state_name) or "").strip().lower()
                        if selected_state in {"allowed", "limited", "denied"}:
                            matrix_states[f"{section['key']}.{action['key']}"] = selected_state
                        else:
                            matrix_states[f"{section['key']}.{action['key']}"] = permission_state_from_flags(
                                allowed=request.POST.get(access_name) == "1",
                                limited=request.POST.get(scope_name) == "1",
                            )
                synced_values = sync_user_permission_fields_from_matrix(matrix_states)
                matrix.matrix_permissions = matrix_states
                for field_name, field_value in synced_values.items():
                    setattr(matrix, field_name, field_value)
                matrix.save(
                    update_fields=[
                        "matrix_permissions",
                        "user_create",
                        "user_read",
                        "user_update",
                        "user_delete",
                        "user_lock",
                        "user_unlock",
                        "user_export",
                        "user_reset_password",
                        "user_audit_view",
                        "updated_at",
                    ]
                )

            record_audit_event(
                actor=request.user,
                event_type="permission_matrix_updated",
                entity_type="role_permission_matrix",
                message="Super admin updated the permission matrix.",
            )
            if wants_json:
                return JsonResponse(
                    {
                        "status": "ok",
                        "message": "Permission matrix updated successfully.",
                    }
                )
            messages.success(request, "Permission matrix updated successfully.")
            return redirect("super-admin-section", section_slug=section_slug)

        if section_slug != "users":
            messages.error(request, "This section does not support inline CRUD actions yet.")
            return redirect("super-admin-section", section_slug=section_slug)

        permissions = self._user_permissions()
        action = (request.POST.get("user_action") or "").strip()
        target_user_id = (request.POST.get("target_user_id") or "").strip()
        selected_user_ids = request.POST.getlist("selected_user_ids")
        target_user = self._user_base_queryset().filter(pk=target_user_id).first() if target_user_id else None

        if action == "bulk":
            bulk_action = (request.POST.get("bulk_action") or "").strip()
            selected_users = self._user_base_queryset().filter(pk__in=selected_user_ids)
            if bulk_action == "export" and permissions["export"]:
                return self._export_users_csv(selected_users, selected_only=True)
            if not selected_users.exists():
                messages.error(request, "Select at least one user to apply a bulk action.")
                return redirect("super-admin-section", section_slug="users")
            action_map = {
                "activate": ("active", None, "activate"),
                "deactivate": ("inactive", None, "deactivate"),
                "lock": (None, True, "lock"),
                "unlock": (None, False, "unlock"),
                "soft_delete": ("deleted", None, "delete"),
            }
            if bulk_action not in action_map:
                messages.error(request, "Unsupported bulk action.")
                return redirect("super-admin-section", section_slug="users")
            new_status, locked, action_label = action_map[bulk_action]
            for user in selected_users:
                self._apply_user_state_change(user, new_status=new_status, locked=locked, action_label=action_label)
            messages.success(request, f"Bulk action '{bulk_action}' applied to {selected_users.count()} users.")
            return redirect("super-admin-section", section_slug="users")

        if action in {"create", "update"}:
            if not permissions["create" if action == "create" else "update"]:
                raise PermissionDenied
            is_create = action == "create"
            form = UserManagementForm(
                request.POST,
                instance=target_user if not is_create else None,
                is_create=is_create,
                current_actor=request.user,
            )
            if form.is_valid():
                old_value = {}
                if target_user:
                    old_value = {
                        "full_name": target_user.full_name,
                        "email": target_user.email,
                        "role": target_user.role,
                        "status": target_user.account_status,
                    }
                user = form.save()
                record_audit_event(
                    actor=request.user,
                    event_type=f"user_{'created' if is_create else 'updated'}",
                    entity_type="user",
                    entity_id=user.pk,
                    message=f"User {user.full_name or user.phone_number} was {'created' if is_create else 'updated'}.",
                    meta={
                        "old_value": old_value,
                        "new_value": {
                            "full_name": user.full_name,
                            "email": user.email,
                            "role": user.role,
                            "status": user.account_status,
                        },
                    },
                )
                messages.success(request, f"{user.full_name or user.phone_number} was {'created' if is_create else 'updated'} successfully.")
                return redirect("super-admin-section", section_slug="users")

            context = self.get_context_data(**kwargs)
            if is_create:
                context["create_user_form"] = form
                context["open_create_user_modal"] = True
            else:
                context["edit_user_form"] = form
                context["open_edit_user_modal"] = True
                context["editing_user_id"] = target_user_id if target_user else ""
            return self.render_to_response(context)

        if target_user is None:
            messages.error(request, "Select a valid user record first.")
            return redirect("super-admin-section", section_slug="users")

        if action == "delete" and permissions["delete"]:
            self._apply_user_state_change(target_user, new_status="deleted", action_label="delete")
            messages.success(request, f"{target_user.full_name or target_user.phone_number} was soft deleted.")
            return redirect("super-admin-section", section_slug="users")
        if action == "activate":
            self._apply_user_state_change(target_user, new_status="active", action_label="activate")
            messages.success(request, f"{target_user.full_name or target_user.phone_number} is now active.")
            return redirect("super-admin-section", section_slug="users")
        if action == "deactivate":
            self._apply_user_state_change(target_user, new_status="inactive", action_label="deactivate")
            messages.success(request, f"{target_user.full_name or target_user.phone_number} is now inactive.")
            return redirect("super-admin-section", section_slug="users")
        if action == "lock" and permissions["lock"]:
            self._apply_user_state_change(target_user, locked=True, action_label="lock")
            messages.success(request, f"{target_user.full_name or target_user.phone_number} was locked.")
            return redirect("super-admin-section", section_slug="users")
        if action == "unlock" and permissions["unlock"]:
            self._apply_user_state_change(target_user, locked=False, action_label="unlock")
            target_user.failed_login_attempts = 0
            target_user.updated_by = request.user
            target_user.save(update_fields=["failed_login_attempts", "updated_by", "updated_at"])
            messages.success(request, f"{target_user.full_name or target_user.phone_number} was unlocked.")
            return redirect("super-admin-section", section_slug="users")
        if action == "reset_password" and permissions["reset_password"]:
            try:
                send_user_password_reset_link(target_user, request=request, initiated_by=request.user)
            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect("super-admin-section", section_slug="users")
            record_audit_event(
                actor=request.user,
                event_type="user_password_reset",
                entity_type="user",
                entity_id=target_user.pk,
                severity="warning",
                message=f"Password reset link issued for {target_user.full_name or target_user.phone_number}.",
            )
            messages.success(request, f"Password reset link sent to {target_user.email}.")
            return redirect("super-admin-section", section_slug="users")
        if action == "resend_verification_email":
            record_audit_event(
                actor=request.user,
                event_type="user_resend_verification_email",
                entity_type="user",
                entity_id=target_user.pk,
                message=f"Verification email reissued for {target_user.full_name or target_user.phone_number}.",
            )
            messages.success(request, f"Verification email resend queued for {target_user.full_name or target_user.phone_number}.")
            return redirect("super-admin-section", section_slug="users")

        messages.error(request, "Unsupported user action.")
        return redirect("super-admin-section", section_slug="users")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        section_slug = (self.kwargs.get("section_slug") or "").strip()
        section_config = self.SECTION_DEFINITIONS.get(section_slug)
        if section_config is None:
            raise PermissionDenied

        metric_groups = []
        for key in section_config.get("metric_keys", []):
            metric_groups.append({"label": key.replace("_", " ").title(), "items": context.get(key, [])})

        table_key = section_config.get("table")
        section_items = context.get(table_key, []) if table_key else []
        if section_slug == "users":
            from platform_apps.audit.models import AuditLog

            filters = self._get_user_filters()
            users_queryset = self._apply_user_filters(self._user_base_queryset(), filters)
            paginator = Paginator(users_queryset, filters["rows"])
            users_page = paginator.get_page(filters["page"])
            users_page.object_list = self._attach_customer_activity_windows(users_page.object_list)
            visible_columns = set(filters["visible_columns"])
            for offset, user in enumerate(users_page.object_list, start=users_page.start_index()):
                user.row_number = offset
                user.edit_url = f"{self.request.path}{self._user_querystring(filters, overrides={'edit': user.pk}, remove=['page'])}"
                user.view_url = f"{self.request.path}{self._user_querystring(filters, overrides={'view': user.pk}, remove=['page'])}"
                user.audit_url = f"{self.request.path}{self._user_querystring(filters, overrides={'audit_user': user.pk}, remove=['page'])}"

            view_user_id = self._safe_int_string(self.request.GET.get("view") or "")
            edit_user_id = self._safe_int_string(self.request.GET.get("edit") or "")
            audit_user_id = self._safe_int_string(self.request.GET.get("audit_user") or "") or view_user_id or edit_user_id
            selected_lookup_id = view_user_id or edit_user_id or audit_user_id
            selected_user = self._user_base_queryset().filter(pk=selected_lookup_id).first() if selected_lookup_id else None
            selected_user_audit = []
            if audit_user_id:
                selected_user_audit = list(
                    AuditLog.objects.filter(entity_type="user", entity_id=str(audit_user_id)).select_related("actor").order_by("-created_at")[:8]
                )

            if not context.get("edit_user_form") and edit_user_id:
                editing_user = self._user_base_queryset().filter(pk=edit_user_id).first()
                if editing_user:
                    context["edit_user_form"] = UserManagementForm(instance=editing_user, is_create=False, current_actor=self.request.user)
                    context["open_edit_user_modal"] = True
                    context["editing_user_id"] = edit_user_id

            pagination_links = []
            for page_num in users_page.paginator.page_range:
                if page_num >= users_page.number - 2 and page_num <= users_page.number + 2:
                    pagination_links.append(
                        {
                            "number": page_num,
                            "active": page_num == users_page.number,
                            "url": f"{self.request.path}{self._user_querystring(filters, overrides={'page': page_num}, remove=['edit', 'view', 'audit_user'])}",
                        }
                    )

            sort_urls = {}
            for column in self.USER_COLUMNS:
                column_key = column["key"]
                if column_key not in {"id", "employee_code", "full_name", "username", "role", "department", "designation", "email", "phone_number", "country", "state", "district", "customer_active_hrs", "account_status", "email_verified", "account_locked", "last_login", "created_at", "updated_at"}:
                    continue
                next_sort = column_key
                if filters["sort"] == column_key:
                    next_sort = f"-{column_key}"
                elif filters["sort"] == f"-{column_key}":
                    next_sort = column_key
                sort_urls[column_key] = f"{self.request.path}{self._user_querystring(filters, overrides={'sort': next_sort}, remove=['page', 'edit', 'view', 'audit_user'])}"
            column_definitions = []
            for column in self.USER_COLUMNS:
                column_definitions.append(
                    {
                        "key": column["key"],
                        "label": column["label"],
                        "visible": column["key"] in visible_columns,
                        "sort_url": sort_urls.get(column["key"], ""),
                    }
                )

            section_items = users_page.object_list
            metric_groups = [{"label": "User KPIs", "items": self._user_metric_cards()}]
            saved_views = list(UserSavedFilterView.objects.filter(owner=self.request.user).order_by("-updated_at")[:8])
            context.update(
                {
                    "users_page": users_page,
                    "user_filters": filters,
                    "user_search_query": filters["q"],
                    "create_user_form": context.get("create_user_form") or UserManagementForm(is_create=True, current_actor=self.request.user),
                    "open_create_user_modal": context.get("open_create_user_modal", False),
                    "edit_user_form": context.get("edit_user_form") or UserManagementForm(is_create=False, current_actor=self.request.user),
                    "open_edit_user_modal": context.get("open_edit_user_modal", False),
                    "editing_user_id": context.get("editing_user_id") or "",
                    "selected_user": selected_user,
                    "selected_user_audit": selected_user_audit,
                    "user_permissions": self._user_permissions(),
                    "user_available_columns": self.USER_COLUMNS,
                    "user_column_definitions": column_definitions,
                    "user_visible_columns": visible_columns,
                    "user_rows_per_page_choices": self.USER_ROWS_PER_PAGE_CHOICES,
                    "user_filter_options": self._user_filter_options(self._user_base_queryset()),
                    "user_prev_page_url": f"{self.request.path}{self._user_querystring(filters, overrides={'page': users_page.previous_page_number()}, remove=['edit', 'view', 'audit_user'])}" if users_page.has_previous() else "",
                    "user_next_page_url": f"{self.request.path}{self._user_querystring(filters, overrides={'page': users_page.next_page_number()}, remove=['edit', 'view', 'audit_user'])}" if users_page.has_next() else "",
                    "user_pagination_links": pagination_links,
                    "user_reset_url": reverse("super-admin-section", kwargs={"section_slug": "users"}),
                    "user_save_view_url": f"{self.request.path}{self._user_querystring(filters, overrides={'save_view': 1}, remove=['page', 'edit', 'view', 'audit_user'])}",
                    "user_apply_saved_view_url": f"{self.request.path}?apply_saved_view=1",
                    "user_saved_view_exists": bool(self.request.session.get("super_admin_users_saved_view")),
                    "user_saved_views": saved_views,
                    "user_export_url": f"{self.request.path}{self._user_querystring(filters, overrides={'export': 'csv'}, remove=['page', 'edit', 'view', 'audit_user'])}",
                    "user_excel_export_url": f"{self.request.path}{self._user_querystring(filters, overrides={'export': 'xls'}, remove=['page', 'edit', 'view', 'audit_user'])}",
                    "user_current_query": self._user_querystring(filters, remove=['page']),
                    "user_sort": filters["sort"],
                    "user_role_catalog_json": json.dumps(self.ROLE_CATALOG),
                    "user_country_states_json": json.dumps(get_country_states_map()),
                }
            )
        elif section_slug == "roles-permissions":
            from .views import build_permission_matrix_sections, ensure_role_permission_matrices

            ensure_role_permission_matrices()
            matrices = list(RolePermissionMatrix.objects.all().order_by("role"))
            permission_matrix_sections = build_permission_matrix_sections(matrices)
            total_actions = sum(len(section["rows"]) for section in permission_matrix_sections)
            total_cells = 0
            allowed_cells = 0
            limited_cells = 0
            denied_cells = 0
            for section in permission_matrix_sections:
                for row in section["rows"]:
                    total_cells += len(row["cells"])
                    for cell in row["cells"]:
                        if cell["state"] == "allowed":
                            allowed_cells += 1
                        elif cell["state"] == "limited":
                            limited_cells += 1
                        else:
                            denied_cells += 1
            section_items = matrices
            context["role_permission_matrices"] = matrices
            context["role_catalog_rows"] = self.ROLE_CATALOG
            context["permission_matrix_sections"] = permission_matrix_sections
            role_catalog_map = {row["role_value"]: row for row in self.ROLE_CATALOG}
            context["permission_matrix_role_headers"] = [
                {
                    "key": matrix.role,
                    "label": matrix.get_role_display(),
                    "meta": (role_catalog_map.get(matrix.role, {}).get("category") or role_catalog_map.get(matrix.role, {}).get("type_of_user") or "Role"),
                }
                for matrix in matrices
            ]
            context["permission_matrix_api_url"] = "/api/v1/auth/admin/users/permissions/"
            context["permission_matrix_legend"] = [
                {"label": "Allowed", "state": "allowed"},
                {"label": "Limited / Scoped", "state": "limited"},
                {"label": "Not allowed", "state": "denied"},
            ]
            context["permission_matrix_summary"] = {
                "roles": len(matrices),
                "modules": len(permission_matrix_sections),
                "actions": total_actions,
                "cells": total_cells,
                "allowed": allowed_cells,
                "limited": limited_cells,
                "denied": denied_cells,
            }

        context.update(
            {
                "section_slug": section_slug,
                "section_page": section_config,
                "section_metric_groups": metric_groups,
                "section_table_key": table_key,
                "section_items": section_items,
                "super_admin_nav": self.build_super_admin_nav(section_slug),
            }
        )
        return context
