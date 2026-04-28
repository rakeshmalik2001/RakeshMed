from __future__ import annotations

from functools import wraps

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.functional import cached_property
from django.views.generic.base import ContextMixin

from .views import user_has_matrix_permission

REQUESTED_ROLE_REDIRECTS = {
    "customer": getattr(settings, "FRONTEND_CUSTOMER_ACCOUNT_URL", "http://localhost:3000/account"),
    "pharmacist": "/pharmacist/dashboard/",
    "vendor": "/vendor/dashboard/",
    "admin": "/admin/dashboard/",
    "super_admin": "/super-admin/dashboard/",
}

LEGACY_ROLE_REDIRECTS = {
    "catalog_manager": "/catalog/dashboard/",
    "warehouse_operator": "/warehouse/dashboard/",
    "delivery_agent": "/delivery/dashboard/",
    "support_agent": "/support/dashboard/",
    "finance": "/finance/dashboard/",
    "operations_manager": "/operations/dashboard/",
    "procurement_manager": "/procurement/dashboard/",
    "compliance_officer": "/compliance/dashboard/",
    "security_admin": "/security/dashboard/",
    "auditor": "/auditor/dashboard/",
    "doctor": "/doctor/dashboard/",
    "marketing_manager": "/marketing/dashboard/",
    "vendor_staff": "/vendor-staff/dashboard/",
    "viewer": "/viewer/dashboard/",
}

ROLE_REDIRECTS = {**LEGACY_ROLE_REDIRECTS, **REQUESTED_ROLE_REDIRECTS}
PUBLIC_REGISTRATION_ROLES = ("pharmacist", "vendor")
ACCOUNT_STATUS_ACTIVE = "active"
ACCOUNT_STATUS_BLOCKED = "blocked"
ACCOUNT_STATUS_SUSPENDED = "suspended"

DASHBOARD_CONTENT = {
    "customer": {
        "title": "Customer Portal Dashboard",
        "subtitle": "Review your orders, prescriptions, addresses, and saved payments from the backend portal surface.",
        "modules": [
            {"title": "Order Snapshot", "text": "Track recent medicine orders and understand current status without leaving the portal."},
            {"title": "Prescription Records", "text": "Review submitted prescriptions, clarifications, and recent approvals in one place."},
            {"title": "Account Shortcuts", "text": "See saved addresses, active payment methods, and notifications alongside quick links to the main customer app."},
        ],
    },
    "pharmacist": {
        "title": "Pharmacist Dashboard",
        "subtitle": "Manage prescription verification, queue health, and customer clarifications.",
        "modules": [
            {"title": "Review Queue", "text": "Work pending approvals and urgent prescription escalations."},
            {"title": "Clinical Decisions", "text": "Track approved, rejected, and clarification-needed cases."},
            {"title": "Patient Safety", "text": "Watch compliance-sensitive events and queue pressure."},
        ],
    },
    "vendor": {
        "title": "Vendor Dashboard",
        "subtitle": "Monitor inventory coverage, catalog readiness, and store operations.",
        "modules": [
            {"title": "Inventory Health", "text": "Check stock posture and items needing replenishment."},
            {"title": "Catalog Control", "text": "See active medicines and availability coverage."},
            {"title": "Order Fulfillment", "text": "Track confirmed orders that depend on store readiness."},
        ],
    },
    "vendor_staff": {
        "title": "Vendor Staff Dashboard",
        "subtitle": "Manage counter operations, stock handling, and assigned store tasks from one staff console.",
        "modules": [
            {"title": "Counter Readiness", "text": "Track assigned order flow, recent stock movement, and store response needs."},
            {"title": "Shelf Coverage", "text": "Monitor low stock rows and recently updated products visible to store staff."},
            {"title": "Staff Workflow", "text": "Review pick, pack, and customer-facing store activity without owner-level controls."},
        ],
    },
    "warehouse_operator": {
        "title": "Warehouse Dashboard",
        "subtitle": "Manage stock pressure, warehouse movement, and fulfillment handoff from one console.",
        "modules": [
            {"title": "Stock Watch", "text": "Monitor low stock rows, receive updates, and dispatch movement."},
            {"title": "Fulfillment Queue", "text": "Track orders waiting to be packed, dispatched, or handed off."},
            {"title": "Movement Log", "text": "Review recent stock activity and warehouse operations."},
        ],
    },
    "delivery_agent": {
        "title": "Delivery Dashboard",
        "subtitle": "Track shipment movement, exceptions, and active delivery operations from one console.",
        "modules": [
            {"title": "Shipment Queue", "text": "Monitor queued, assigned, and in-transit shipments."},
            {"title": "Delivery Exceptions", "text": "Review failed, returned, and reattempt-due deliveries."},
            {"title": "Movement Timeline", "text": "Watch active shipment status updates and route flow."},
        ],
    },
    "support_agent": {
        "title": "Support Dashboard",
        "subtitle": "Understand customer, order, prescription, and account signals before every support response.",
        "modules": [
            {"title": "Customer Signals", "text": "Monitor account health, notifications, and recent customer activity."},
            {"title": "Order Assist", "text": "Track recent orders, delays, and statuses that often drive support needs."},
            {"title": "Prescription Assist", "text": "Review prescription status changes and clarification-sensitive cases."},
        ],
    },
    "finance": {
        "title": "Finance Dashboard",
        "subtitle": "Track revenue, payment quality, refund flow, and settlement activity from one console.",
        "modules": [
            {"title": "Revenue Watch", "text": "Monitor paid order totals and captured payment volume."},
            {"title": "Refund Flow", "text": "Review pending, processed, and rejected refund activity."},
            {"title": "Settlement Control", "text": "Track settlement batches and finance reconciliation signals."},
        ],
    },
    "security_admin": {
        "title": "Security Dashboard",
        "subtitle": "Monitor login risk, account controls, and privileged audit activity from one console.",
        "modules": [
            {"title": "Authentication Risk", "text": "Watch failed logins, MFA posture, and account lock pressure."},
            {"title": "Control Center", "text": "Track blocked users, suspended access, and response-needed accounts."},
            {"title": "Audit Watch", "text": "Review critical events and recent privileged control actions."},
        ],
    },
    "doctor": {
        "title": "Doctor Dashboard",
        "subtitle": "Review doctor-linked prescription flow, clinical throughput, and recent prescription activity.",
        "modules": [
            {"title": "Clinical Queue", "text": "Track pending, approved, and clarification-sensitive prescription flow."},
            {"title": "Doctor Activity", "text": "Monitor doctor-linked prescription volume and distinct doctor coverage."},
            {"title": "Recent Cases", "text": "Review the latest prescription records linked to doctors and patient demand."},
        ],
    },
    "operations_manager": {
        "title": "Operations Dashboard",
        "subtitle": "Monitor approvals, order throughput, inventory pressure, and delivery readiness from one console.",
        "modules": [
            {"title": "Approval Flow", "text": "Track pending, overdue, and unassigned onboarding requests."},
            {"title": "Commerce Throughput", "text": "Watch orders waiting on payment, prescription review, and fulfillment."},
            {"title": "Fulfillment Pressure", "text": "Review low-stock rows, shipment readiness, and active delivery flow."},
        ],
    },
    "catalog_manager": {
        "title": "Catalog Dashboard",
        "subtitle": "Manage medicine coverage, category structure, brand mix, and substitute readiness from one console.",
        "modules": [
            {"title": "Catalog Coverage", "text": "Watch active products, prescription-required medicines, and stock posture."},
            {"title": "Structure Health", "text": "Track categories, brands, and visibility across the medicine catalog."},
            {"title": "Substitute Network", "text": "Review substitute links and the latest catalog updates needing attention."},
        ],
    },
    "procurement_manager": {
        "title": "Procurement Dashboard",
        "subtitle": "Track replenishment pressure, inbound stock, and restock-sensitive medicines from one console.",
        "modules": [
            {"title": "Replenishment Watch", "text": "Monitor low-stock and out-of-stock medicines needing procurement action."},
            {"title": "Inbound Coverage", "text": "Review inbound quantities and active stock positions across locations."},
            {"title": "Restock Activity", "text": "Track recent restocks, transfer-ins, and inventory rows needing follow-up."},
        ],
    },
    "marketing_manager": {
        "title": "Marketing Dashboard",
        "subtitle": "Track customer demand, website activity, catalog mix, and campaign-facing signals from one console.",
        "modules": [
            {"title": "Audience Activity", "text": "Monitor active customer sessions, weekly usage, and recent engagement."},
            {"title": "Demand Signals", "text": "Track order, prescription, and category activity shaping campaigns."},
            {"title": "Catalog Focus", "text": "Review OTC, prescription, and highlighted product mix for promotions."},
        ],
    },
    "compliance_officer": {
        "title": "Compliance Dashboard",
        "subtitle": "Track audit activity, approval exceptions, and prescription risk signals from one console.",
        "modules": [
            {"title": "Audit Visibility", "text": "Review recent audit activity with emphasis on warning and critical events."},
            {"title": "Approval Exceptions", "text": "Watch rejected documents, overdue approvals, and unresolved onboarding risk."},
            {"title": "Clinical Compliance", "text": "Track clarification-required and rejected prescriptions needing compliance attention."},
        ],
    },
    "auditor": {
        "title": "Auditor Dashboard",
        "subtitle": "Review platform evidence, audit history, and operational traces from a read-only audit console.",
        "modules": [
            {"title": "Audit Evidence", "text": "Track warning, critical, and control-changing audit records."},
            {"title": "Operational Trace", "text": "Review order, prescription, and inventory evidence trails."},
            {"title": "Approval Trail", "text": "Watch approval status shifts, document decisions, and SLA escalation evidence."},
        ],
    },
    "viewer": {
        "title": "Viewer Dashboard",
        "subtitle": "Monitor platform visibility, read live activity, and review operational signals without edit permissions.",
        "modules": [
            {"title": "Platform Snapshot", "text": "See high-level user, order, and prescription counts from one read-only console."},
            {"title": "Operational Watch", "text": "Track recent orders, active inventory pressure, and unread platform alerts."},
            {"title": "Visibility Feed", "text": "Review recent notifications, prescription movement, and monitoring signals."},
        ],
    },
    "admin": {
        "title": "Admin Dashboard",
        "subtitle": "See high-level operations, user management, and day-to-day pharmacy activity.",
        "modules": [
            {"title": "Operations", "text": "Watch orders, users, and prescription flow from one console."},
            {"title": "User Control", "text": "Manage role assignments, statuses, and access exceptions."},
            {"title": "Audit Trails", "text": "Review privileged actions and account events."},
        ],
    },
    "super_admin": {
        "title": "Super Admin Dashboard",
        "subtitle": "Full platform control with privileged visibility across access, operations, and security.",
        "modules": [
            {"title": "Global Access", "text": "Override role restrictions and manage privileged accounts."},
            {"title": "Security Oversight", "text": "Review blocked logins, account suspensions, and audit signals."},
            {"title": "Platform Health", "text": "Inspect users, prescriptions, inventory, orders, and notifications."},
        ],
    },
}


def resolve_dashboard_url(user) -> str:
    role = getattr(user, "role", "")
    return ROLE_REDIRECTS.get(role, reverse("login"))


def has_role_access(user, allowed_roles: tuple[str, ...] | list[str] | set[str]) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    if getattr(user, "role", "") not in allowed_roles:
        return False
    return user_has_matrix_permission(user, "core_access.dashboard_access")


def render_access_denied(request: HttpRequest, *, allowed_roles=()) -> HttpResponse:
    return render(
        request,
        "errors/access_denied.html",
        {
            "allowed_roles": allowed_roles,
            "dashboard_url": resolve_dashboard_url(request.user) if request.user.is_authenticated else reverse("login"),
        },
        status=403,
    )


def role_required(*allowed_roles: str):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped(request: HttpRequest, *args, **kwargs):
            if not has_role_access(request.user, allowed_roles):
                return render_access_denied(request, allowed_roles=allowed_roles)
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


class RoleContextMixin(ContextMixin):
    allowed_roles: tuple[str, ...] = ()

    @cached_property
    def current_role(self) -> str:
        return getattr(self.request.user, "role", "")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard_url"] = resolve_dashboard_url(self.request.user)
        context["current_role"] = self.current_role
        return context


class RoleRequiredMixin(RoleContextMixin):
    allowed_roles: tuple[str, ...] = ()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login

            return redirect_to_login(request.get_full_path())
        if not has_role_access(request.user, self.allowed_roles):
            return render_access_denied(request, allowed_roles=self.allowed_roles)
        return super().dispatch(request, *args, **kwargs)
