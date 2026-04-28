import csv
import random
import re
from io import StringIO

from django.conf import settings
from django.db import transaction
from django.db.models import F, Q, Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import generics
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.decorators import throttle_classes
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from platform_apps.audit.services import record_audit_event

from .location_catalog import get_all_countries, get_districts_of_state, get_states_of_country
from .models import CustomerAddress, CustomerWebsiteActivityDaily, OTPRequest, RolePermissionMatrix, SavedPaymentMethod, User, UserSavedFilterView, format_active_duration
from .serializers import (
    AdminUserManagementSerializer,
    CustomerAddressSerializer,
    RolePermissionMatrixSerializer,
    SavedPaymentMethodSerializer,
    SendOTPSerializer,
    UserSerializer,
    UserSavedFilterViewSerializer,
    UserProfileUpdateSerializer,
    VerifyOTPSerializer,
)
from .throttles import AuthSendOtpThrottle, AuthVerifyOtpThrottle
from .services import send_user_password_reset_link


def _generate_otp_code() -> str:
    return f"{random.randint(0, 999999):06d}"


def _token_expiry_for(token) -> timezone.datetime | None:
    ttl_seconds = int(getattr(settings, "AUTH_TOKEN_TTL_SECONDS", 0) or 0)
    if ttl_seconds <= 0 or token is None:
        return None
    return token.created + timezone.timedelta(seconds=ttl_seconds)


def _request_ip(request) -> str:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


PUBLIC_OTP_LOGIN_ALLOWED_ROLES = {"customer"}


def _record_customer_activity_heartbeat(user: User, *, tab_id: str) -> dict[str, object]:
    now = timezone.now()
    counted_seconds = 0
    counted = False

    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(pk=user.pk)
        previous_tab_id = locked_user.customer_activity_active_tab_id or ""
        previous_seen_at = locked_user.customer_activity_active_tab_seen_at
        tab_lease_is_fresh = bool(previous_seen_at and previous_seen_at >= now - timezone.timedelta(seconds=CUSTOMER_ACTIVITY_TAB_LEASE_SECONDS))

        if previous_tab_id and previous_tab_id != tab_id and tab_lease_is_fresh:
            return {
                "status": "ignored",
                "reason": "another_tab_active",
                "counted_seconds": 0,
                "total_seconds": locked_user.customer_active_seconds_total,
                "total_label": locked_user.customer_active_duration_label,
            }

        if previous_tab_id == tab_id and previous_seen_at:
            elapsed_seconds = int((now - previous_seen_at).total_seconds())
            if 0 < elapsed_seconds <= CUSTOMER_ACTIVITY_IDLE_TIMEOUT_SECONDS:
                counted_seconds = min(elapsed_seconds, CUSTOMER_ACTIVITY_HEARTBEAT_CAP_SECONDS)
                counted = counted_seconds > 0

        locked_user.customer_activity_active_tab_id = tab_id
        locked_user.customer_activity_active_tab_seen_at = now
        if counted:
            locked_user.customer_active_seconds_total = F("customer_active_seconds_total") + counted_seconds
        locked_user.save(
            update_fields=[
                "customer_activity_active_tab_id",
                "customer_activity_active_tab_seen_at",
                "customer_active_seconds_total",
                "updated_at",
            ]
        )

        if counted:
            activity_day, _created = CustomerWebsiteActivityDaily.objects.select_for_update().get_or_create(
                user=locked_user,
                activity_date=timezone.localdate(now),
                defaults={"last_heartbeat_at": now},
            )
            activity_day.active_seconds = F("active_seconds") + counted_seconds
            activity_day.heartbeat_count = F("heartbeat_count") + 1
            activity_day.last_heartbeat_at = now
            activity_day.save(update_fields=["active_seconds", "heartbeat_count", "last_heartbeat_at", "updated_at"])

        locked_user.refresh_from_db(fields=["customer_active_seconds_total"])

    return {
        "status": "counted" if counted else "resumed",
        "counted_seconds": counted_seconds,
        "total_seconds": locked_user.customer_active_seconds_total,
        "total_label": locked_user.customer_active_duration_label,
    }


def _serialize_admin_user_lookup(user: User) -> dict[str, object]:
    return {
        "id": user.pk,
        "employee_code": user.employee_code or "",
        "username": user.username or "",
        "full_name": user.full_name or "",
        "type_of_user": user.type_of_user or "",
        "type_of_user_label": user.get_type_of_user_display(),
        "role": user.role or "",
        "role_label": user.get_role_display(),
        "department": user.department or "",
        "designation": user.designation or "",
        "email": user.email or "",
        "phone_number": user.phone_number or "",
        "country": user.country or "",
        "state": user.state or "",
        "district": user.district or "",
        "address": user.address or "",
        "account_status": user.account_status or "",
        "account_status_label": user.get_account_status_display(),
        "email_verified": user.email_verified,
        "account_locked": user.account_locked,
        "mfa_enabled": user.mfa_enabled,
        "remarks": user.remarks or "",
    }


CUSTOMER_ACTIVITY_IDLE_TIMEOUT_SECONDS = 5 * 60
CUSTOMER_ACTIVITY_HEARTBEAT_CAP_SECONDS = 45
CUSTOMER_ACTIVITY_TAB_LEASE_SECONDS = 45
CUSTOMER_ACTIVITY_TAB_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


USER_PERMISSION_FIELD_MAP = {
    "create": "user_create",
    "read": "user_read",
    "update": "user_update",
    "delete": "user_delete",
    "lock": "user_lock",
    "unlock": "user_unlock",
    "export": "user_export",
    "reset_password": "user_reset_password",
    "audit_view": "user_audit_view",
}


PERMISSION_STATE_ALLOWED = "allowed"
PERMISSION_STATE_DENIED = "denied"
PERMISSION_STATE_LIMITED = "limited"
PERMISSION_STATE_CHOICES = {PERMISSION_STATE_ALLOWED, PERMISSION_STATE_DENIED, PERMISSION_STATE_LIMITED}

PERMISSION_MATRIX_SECTIONS = [
    {
        "key": "core_access",
        "title": "Core Access Matrix",
        "icon": "grid-1x2",
        "roles": [
            "customer",
            "vendor",
            "vendor_staff",
            "pharmacist",
            "doctor",
            "warehouse_operator",
            "delivery_agent",
            "support_agent",
            "finance",
            "catalog_manager",
            "operations_manager",
            "admin",
            "compliance_officer",
            "auditor",
            "viewer",
            "security_admin",
            "super_admin",
        ],
        "actions": [
            {"key": "dashboard_access", "label": "Dashboard Access"},
            {"key": "profile_own", "label": "Profile (Own)"},
            {"key": "profile_others", "label": "Profile (Others)"},
        ],
    },
    {
        "key": "medicine_catalog",
        "title": "Medicine / Catalog",
        "icon": "capsule",
        "roles": ["customer", "vendor", "vendor_staff", "catalog_manager", "admin", "super_admin"],
        "actions": [
            {"key": "view_medicines", "label": "View Medicines"},
            {"key": "add_medicine", "label": "Add Medicine"},
            {"key": "edit_medicine", "label": "Edit Medicine"},
            {"key": "delete_medicine", "label": "Delete Medicine"},
            {"key": "approve_medicine", "label": "Approve Medicine"},
            {"key": "bulk_upload", "label": "Bulk Upload"},
        ],
    },
    {
        "key": "prescription_management",
        "title": "Prescription Management",
        "icon": "file-earmark-medical",
        "roles": ["customer", "pharmacist", "doctor", "vendor", "admin", "super_admin"],
        "actions": [
            {"key": "upload", "label": "Upload"},
            {"key": "view", "label": "View"},
            {"key": "approve", "label": "Approve"},
            {"key": "reject", "label": "Reject"},
        ],
    },
    {
        "key": "orders",
        "title": "Orders",
        "icon": "box-seam",
        "roles": ["customer", "vendor", "warehouse_operator", "delivery_agent", "support_agent", "admin", "super_admin"],
        "actions": [
            {"key": "create_order", "label": "Create Order"},
            {"key": "view_orders", "label": "View Orders"},
            {"key": "process_order", "label": "Process Order"},
            {"key": "cancel_order", "label": "Cancel Order"},
            {"key": "assign_order", "label": "Assign Order"},
        ],
    },
    {
        "key": "inventory_warehouse",
        "title": "Inventory / Warehouse",
        "icon": "boxes",
        "roles": ["vendor", "warehouse_operator", "admin", "super_admin"],
        "actions": [
            {"key": "view_stock", "label": "View Stock"},
            {"key": "add_stock", "label": "Add Stock"},
            {"key": "update_stock", "label": "Update Stock"},
            {"key": "dispatch", "label": "Dispatch"},
            {"key": "receive_stock", "label": "Receive Stock"},
        ],
    },
    {
        "key": "finance",
        "title": "Finance",
        "icon": "currency-rupee",
        "roles": ["customer", "vendor", "finance", "admin", "super_admin"],
        "actions": [
            {"key": "make_payment", "label": "Make Payment"},
            {"key": "view_transactions", "label": "View Transactions"},
            {"key": "refund", "label": "Refund"},
            {"key": "payouts", "label": "Payouts"},
        ],
    },
    {
        "key": "user_management",
        "title": "User Management",
        "icon": "people",
        "roles": ["support_agent", "admin", "super_admin"],
        "actions": [
            {"key": "view_users", "label": "View Users"},
            {"key": "create_users", "label": "Create Users"},
            {"key": "edit_users", "label": "Edit Users"},
            {"key": "delete_users", "label": "Delete Users"},
            {"key": "assign_roles", "label": "Assign Roles"},
        ],
    },
    {
        "key": "reports",
        "title": "Reports",
        "icon": "bar-chart",
        "roles": ["viewer", "vendor", "finance", "admin", "super_admin"],
        "actions": [
            {"key": "view_reports", "label": "View Reports"},
            {"key": "export_reports", "label": "Export Reports"},
        ],
    },
    {
        "key": "support_tickets",
        "title": "Support / Tickets",
        "icon": "headset",
        "roles": ["customer", "support_agent", "admin", "super_admin"],
        "actions": [
            {"key": "create_ticket", "label": "Create Ticket"},
            {"key": "view_tickets", "label": "View Tickets"},
            {"key": "reply", "label": "Reply"},
            {"key": "close_ticket", "label": "Close Ticket"},
        ],
    },
    {
        "key": "security_audit",
        "title": "Security & Audit",
        "icon": "shield-lock",
        "roles": ["admin", "compliance_officer", "auditor", "security_admin", "super_admin"],
        "actions": [
            {"key": "view_logs", "label": "View Logs"},
            {"key": "audit_data", "label": "Audit Data"},
            {"key": "security_control", "label": "Security Control"},
            {"key": "block_users", "label": "Block Users"},
        ],
    },
    {
        "key": "settings",
        "title": "Settings",
        "icon": "gear",
        "roles": ["customer", "vendor", "admin", "security_admin", "super_admin"],
        "actions": [
            {"key": "personal_settings", "label": "Personal Settings"},
            {"key": "store_settings", "label": "Store Settings"},
            {"key": "platform_settings", "label": "Platform Settings"},
            {"key": "security_settings", "label": "Security Settings"},
        ],
    },
]

PERMISSION_MATRIX_DEFAULTS = {
    "customer": {
        "core_access.dashboard_access": PERMISSION_STATE_ALLOWED,
        "core_access.profile_own": PERMISSION_STATE_ALLOWED,
        "medicine_catalog.view_medicines": PERMISSION_STATE_ALLOWED,
        "prescription_management.upload": PERMISSION_STATE_ALLOWED,
        "prescription_management.view": PERMISSION_STATE_LIMITED,
        "orders.create_order": PERMISSION_STATE_ALLOWED,
        "orders.view_orders": PERMISSION_STATE_LIMITED,
        "orders.cancel_order": PERMISSION_STATE_LIMITED,
        "finance.make_payment": PERMISSION_STATE_ALLOWED,
        "finance.view_transactions": PERMISSION_STATE_LIMITED,
        "support_tickets.create_ticket": PERMISSION_STATE_ALLOWED,
        "support_tickets.view_tickets": PERMISSION_STATE_LIMITED,
        "support_tickets.reply": PERMISSION_STATE_LIMITED,
        "settings.personal_settings": PERMISSION_STATE_ALLOWED,
    },
    "vendor": {
        "core_access.dashboard_access": PERMISSION_STATE_ALLOWED,
        "core_access.profile_own": PERMISSION_STATE_ALLOWED,
        "medicine_catalog.view_medicines": PERMISSION_STATE_ALLOWED,
        "medicine_catalog.add_medicine": PERMISSION_STATE_LIMITED,
        "medicine_catalog.edit_medicine": PERMISSION_STATE_LIMITED,
        "medicine_catalog.delete_medicine": PERMISSION_STATE_LIMITED,
        "medicine_catalog.bulk_upload": PERMISSION_STATE_LIMITED,
        "prescription_management.view": PERMISSION_STATE_LIMITED,
        "orders.view_orders": PERMISSION_STATE_LIMITED,
        "orders.process_order": PERMISSION_STATE_ALLOWED,
        "orders.cancel_order": PERMISSION_STATE_LIMITED,
        "inventory_warehouse.view_stock": PERMISSION_STATE_ALLOWED,
        "inventory_warehouse.add_stock": PERMISSION_STATE_ALLOWED,
        "inventory_warehouse.update_stock": PERMISSION_STATE_ALLOWED,
        "finance.view_transactions": PERMISSION_STATE_LIMITED,
        "finance.payouts": PERMISSION_STATE_LIMITED,
        "reports.view_reports": PERMISSION_STATE_LIMITED,
        "reports.export_reports": PERMISSION_STATE_LIMITED,
        "settings.personal_settings": PERMISSION_STATE_ALLOWED,
        "settings.store_settings": PERMISSION_STATE_ALLOWED,
    },
    "vendor_staff": {
        "core_access.dashboard_access": PERMISSION_STATE_ALLOWED,
        "core_access.profile_own": PERMISSION_STATE_ALLOWED,
        "medicine_catalog.view_medicines": PERMISSION_STATE_ALLOWED,
        "medicine_catalog.add_medicine": PERMISSION_STATE_LIMITED,
        "medicine_catalog.edit_medicine": PERMISSION_STATE_LIMITED,
        "orders.view_orders": PERMISSION_STATE_LIMITED,
    },
    "pharmacist": {
        "core_access.dashboard_access": PERMISSION_STATE_ALLOWED,
        "core_access.profile_own": PERMISSION_STATE_ALLOWED,
        "prescription_management.view": PERMISSION_STATE_LIMITED,
        "prescription_management.approve": PERMISSION_STATE_ALLOWED,
        "prescription_management.reject": PERMISSION_STATE_ALLOWED,
    },
    "doctor": {
        "core_access.dashboard_access": PERMISSION_STATE_ALLOWED,
        "core_access.profile_own": PERMISSION_STATE_ALLOWED,
        "prescription_management.view": PERMISSION_STATE_LIMITED,
        "prescription_management.approve": PERMISSION_STATE_LIMITED,
        "prescription_management.reject": PERMISSION_STATE_LIMITED,
    },
    "warehouse_operator": {
        "core_access.dashboard_access": PERMISSION_STATE_ALLOWED,
        "core_access.profile_own": PERMISSION_STATE_ALLOWED,
        "orders.view_orders": PERMISSION_STATE_LIMITED,
        "orders.process_order": PERMISSION_STATE_LIMITED,
        "inventory_warehouse.view_stock": PERMISSION_STATE_ALLOWED,
        "inventory_warehouse.add_stock": PERMISSION_STATE_ALLOWED,
        "inventory_warehouse.update_stock": PERMISSION_STATE_ALLOWED,
        "inventory_warehouse.dispatch": PERMISSION_STATE_ALLOWED,
        "inventory_warehouse.receive_stock": PERMISSION_STATE_ALLOWED,
    },
    "delivery_agent": {
        "core_access.dashboard_access": PERMISSION_STATE_ALLOWED,
        "core_access.profile_own": PERMISSION_STATE_ALLOWED,
        "orders.view_orders": PERMISSION_STATE_LIMITED,
    },
    "support_agent": {
        "core_access.dashboard_access": PERMISSION_STATE_ALLOWED,
        "core_access.profile_own": PERMISSION_STATE_ALLOWED,
        "core_access.profile_others": PERMISSION_STATE_LIMITED,
        "orders.view_orders": PERMISSION_STATE_LIMITED,
        "user_management.view_users": PERMISSION_STATE_LIMITED,
        "support_tickets.create_ticket": PERMISSION_STATE_ALLOWED,
        "support_tickets.view_tickets": PERMISSION_STATE_LIMITED,
        "support_tickets.reply": PERMISSION_STATE_ALLOWED,
        "support_tickets.close_ticket": PERMISSION_STATE_ALLOWED,
    },
    "finance": {
        "core_access.dashboard_access": PERMISSION_STATE_ALLOWED,
        "core_access.profile_own": PERMISSION_STATE_ALLOWED,
        "core_access.profile_others": PERMISSION_STATE_LIMITED,
        "finance.view_transactions": PERMISSION_STATE_ALLOWED,
        "finance.refund": PERMISSION_STATE_ALLOWED,
        "finance.payouts": PERMISSION_STATE_ALLOWED,
        "reports.view_reports": PERMISSION_STATE_ALLOWED,
        "reports.export_reports": PERMISSION_STATE_ALLOWED,
    },
    "catalog_manager": {
        "core_access.dashboard_access": PERMISSION_STATE_ALLOWED,
        "core_access.profile_own": PERMISSION_STATE_ALLOWED,
        "medicine_catalog.view_medicines": PERMISSION_STATE_ALLOWED,
        "medicine_catalog.add_medicine": PERMISSION_STATE_ALLOWED,
        "medicine_catalog.edit_medicine": PERMISSION_STATE_ALLOWED,
        "medicine_catalog.delete_medicine": PERMISSION_STATE_ALLOWED,
        "medicine_catalog.bulk_upload": PERMISSION_STATE_ALLOWED,
    },
    "procurement_manager": {
        "core_access.dashboard_access": PERMISSION_STATE_ALLOWED,
        "core_access.profile_own": PERMISSION_STATE_ALLOWED,
        "inventory_warehouse.view_stock": PERMISSION_STATE_ALLOWED,
        "inventory_warehouse.receive_stock": PERMISSION_STATE_LIMITED,
        "reports.view_reports": PERMISSION_STATE_LIMITED,
    },
    "marketing_manager": {
        "core_access.dashboard_access": PERMISSION_STATE_ALLOWED,
        "core_access.profile_own": PERMISSION_STATE_ALLOWED,
        "medicine_catalog.view_medicines": PERMISSION_STATE_ALLOWED,
        "orders.view_orders": PERMISSION_STATE_LIMITED,
        "reports.view_reports": PERMISSION_STATE_ALLOWED,
    },
    "operations_manager": {
        "core_access.dashboard_access": PERMISSION_STATE_ALLOWED,
        "core_access.profile_own": PERMISSION_STATE_ALLOWED,
        "core_access.profile_others": PERMISSION_STATE_LIMITED,
    },
    "admin": {
        "core_access.dashboard_access": PERMISSION_STATE_ALLOWED,
        "core_access.profile_own": PERMISSION_STATE_ALLOWED,
        "core_access.profile_others": PERMISSION_STATE_ALLOWED,
        "medicine_catalog.view_medicines": PERMISSION_STATE_ALLOWED,
        "medicine_catalog.add_medicine": PERMISSION_STATE_ALLOWED,
        "medicine_catalog.edit_medicine": PERMISSION_STATE_ALLOWED,
        "medicine_catalog.delete_medicine": PERMISSION_STATE_ALLOWED,
        "medicine_catalog.approve_medicine": PERMISSION_STATE_ALLOWED,
        "medicine_catalog.bulk_upload": PERMISSION_STATE_ALLOWED,
        "prescription_management.view": PERMISSION_STATE_ALLOWED,
        "prescription_management.approve": PERMISSION_STATE_ALLOWED,
        "prescription_management.reject": PERMISSION_STATE_ALLOWED,
        "orders.create_order": PERMISSION_STATE_LIMITED,
        "orders.view_orders": PERMISSION_STATE_ALLOWED,
        "orders.process_order": PERMISSION_STATE_ALLOWED,
        "orders.cancel_order": PERMISSION_STATE_ALLOWED,
        "orders.assign_order": PERMISSION_STATE_ALLOWED,
        "inventory_warehouse.view_stock": PERMISSION_STATE_ALLOWED,
        "inventory_warehouse.add_stock": PERMISSION_STATE_ALLOWED,
        "inventory_warehouse.update_stock": PERMISSION_STATE_ALLOWED,
        "inventory_warehouse.dispatch": PERMISSION_STATE_ALLOWED,
        "inventory_warehouse.receive_stock": PERMISSION_STATE_ALLOWED,
        "finance.view_transactions": PERMISSION_STATE_ALLOWED,
        "finance.refund": PERMISSION_STATE_ALLOWED,
        "finance.payouts": PERMISSION_STATE_ALLOWED,
        "user_management.view_users": PERMISSION_STATE_ALLOWED,
        "user_management.create_users": PERMISSION_STATE_ALLOWED,
        "user_management.edit_users": PERMISSION_STATE_ALLOWED,
        "user_management.delete_users": PERMISSION_STATE_LIMITED,
        "user_management.assign_roles": PERMISSION_STATE_LIMITED,
        "reports.view_reports": PERMISSION_STATE_ALLOWED,
        "reports.export_reports": PERMISSION_STATE_ALLOWED,
        "support_tickets.create_ticket": PERMISSION_STATE_ALLOWED,
        "support_tickets.view_tickets": PERMISSION_STATE_ALLOWED,
        "support_tickets.reply": PERMISSION_STATE_ALLOWED,
        "support_tickets.close_ticket": PERMISSION_STATE_ALLOWED,
        "security_audit.view_logs": PERMISSION_STATE_LIMITED,
        "security_audit.block_users": PERMISSION_STATE_ALLOWED,
        "settings.personal_settings": PERMISSION_STATE_ALLOWED,
        "settings.store_settings": PERMISSION_STATE_ALLOWED,
        "settings.platform_settings": PERMISSION_STATE_LIMITED,
    },
    "compliance_officer": {
        "core_access.dashboard_access": PERMISSION_STATE_ALLOWED,
        "core_access.profile_own": PERMISSION_STATE_ALLOWED,
        "core_access.profile_others": PERMISSION_STATE_LIMITED,
        "security_audit.view_logs": PERMISSION_STATE_LIMITED,
        "security_audit.audit_data": PERMISSION_STATE_ALLOWED,
    },
    "auditor": {
        "core_access.dashboard_access": PERMISSION_STATE_ALLOWED,
        "core_access.profile_own": PERMISSION_STATE_LIMITED,
        "core_access.profile_others": PERMISSION_STATE_LIMITED,
        "reports.view_reports": PERMISSION_STATE_LIMITED,
        "security_audit.view_logs": PERMISSION_STATE_LIMITED,
        "security_audit.audit_data": PERMISSION_STATE_ALLOWED,
    },
    "viewer": {
        "core_access.dashboard_access": PERMISSION_STATE_LIMITED,
        "core_access.profile_own": PERMISSION_STATE_LIMITED,
        "orders.view_orders": PERMISSION_STATE_LIMITED,
        "inventory_warehouse.view_stock": PERMISSION_STATE_LIMITED,
        "reports.view_reports": PERMISSION_STATE_LIMITED,
    },
    "security_admin": {
        "core_access.dashboard_access": PERMISSION_STATE_ALLOWED,
        "core_access.profile_own": PERMISSION_STATE_ALLOWED,
        "core_access.profile_others": PERMISSION_STATE_ALLOWED,
        "security_audit.view_logs": PERMISSION_STATE_ALLOWED,
        "security_audit.audit_data": PERMISSION_STATE_LIMITED,
        "security_audit.security_control": PERMISSION_STATE_ALLOWED,
        "security_audit.block_users": PERMISSION_STATE_ALLOWED,
        "settings.personal_settings": PERMISSION_STATE_ALLOWED,
        "settings.security_settings": PERMISSION_STATE_ALLOWED,
        "settings.platform_settings": PERMISSION_STATE_LIMITED,
    },
    "super_admin": {
        "core_access.dashboard_access": PERMISSION_STATE_ALLOWED,
        "core_access.profile_own": PERMISSION_STATE_ALLOWED,
        "core_access.profile_others": PERMISSION_STATE_ALLOWED,
        "medicine_catalog.view_medicines": PERMISSION_STATE_ALLOWED,
        "medicine_catalog.add_medicine": PERMISSION_STATE_ALLOWED,
        "medicine_catalog.edit_medicine": PERMISSION_STATE_ALLOWED,
        "medicine_catalog.delete_medicine": PERMISSION_STATE_ALLOWED,
        "medicine_catalog.approve_medicine": PERMISSION_STATE_ALLOWED,
        "medicine_catalog.bulk_upload": PERMISSION_STATE_ALLOWED,
        "prescription_management.view": PERMISSION_STATE_ALLOWED,
        "prescription_management.approve": PERMISSION_STATE_ALLOWED,
        "prescription_management.reject": PERMISSION_STATE_ALLOWED,
        "orders.create_order": PERMISSION_STATE_ALLOWED,
        "orders.view_orders": PERMISSION_STATE_ALLOWED,
        "orders.process_order": PERMISSION_STATE_ALLOWED,
        "orders.cancel_order": PERMISSION_STATE_ALLOWED,
        "orders.assign_order": PERMISSION_STATE_ALLOWED,
        "inventory_warehouse.view_stock": PERMISSION_STATE_ALLOWED,
        "inventory_warehouse.add_stock": PERMISSION_STATE_ALLOWED,
        "inventory_warehouse.update_stock": PERMISSION_STATE_ALLOWED,
        "inventory_warehouse.dispatch": PERMISSION_STATE_ALLOWED,
        "inventory_warehouse.receive_stock": PERMISSION_STATE_ALLOWED,
        "finance.make_payment": PERMISSION_STATE_ALLOWED,
        "finance.view_transactions": PERMISSION_STATE_ALLOWED,
        "finance.refund": PERMISSION_STATE_ALLOWED,
        "finance.payouts": PERMISSION_STATE_ALLOWED,
        "user_management.view_users": PERMISSION_STATE_ALLOWED,
        "user_management.create_users": PERMISSION_STATE_ALLOWED,
        "user_management.edit_users": PERMISSION_STATE_ALLOWED,
        "user_management.delete_users": PERMISSION_STATE_ALLOWED,
        "user_management.assign_roles": PERMISSION_STATE_ALLOWED,
        "reports.view_reports": PERMISSION_STATE_ALLOWED,
        "reports.export_reports": PERMISSION_STATE_ALLOWED,
        "support_tickets.create_ticket": PERMISSION_STATE_ALLOWED,
        "support_tickets.view_tickets": PERMISSION_STATE_ALLOWED,
        "support_tickets.reply": PERMISSION_STATE_ALLOWED,
        "support_tickets.close_ticket": PERMISSION_STATE_ALLOWED,
        "security_audit.view_logs": PERMISSION_STATE_ALLOWED,
        "security_audit.audit_data": PERMISSION_STATE_ALLOWED,
        "security_audit.security_control": PERMISSION_STATE_ALLOWED,
        "security_audit.block_users": PERMISSION_STATE_ALLOWED,
        "settings.personal_settings": PERMISSION_STATE_ALLOWED,
        "settings.store_settings": PERMISSION_STATE_ALLOWED,
        "settings.platform_settings": PERMISSION_STATE_ALLOWED,
        "settings.security_settings": PERMISSION_STATE_ALLOWED,
    },
}


def iter_permission_matrix_keys():
    for section in PERMISSION_MATRIX_SECTIONS:
        for action in section["actions"]:
            yield f"{section['key']}.{action['key']}"


def build_default_permission_matrix_states(role: str) -> dict[str, str]:
    states = {key: PERMISSION_STATE_DENIED for key in iter_permission_matrix_keys()}
    states.update(PERMISSION_MATRIX_DEFAULTS.get(role, {}))
    return states


def normalize_permission_matrix_states(role: str, stored_permissions=None) -> dict[str, str]:
    states = build_default_permission_matrix_states(role)
    if isinstance(stored_permissions, dict):
        for key, value in stored_permissions.items():
            if key in states and value in PERMISSION_STATE_CHOICES:
                states[key] = value
    return states


def permission_state_from_flags(*, allowed: bool, limited: bool) -> str:
    if limited:
        return PERMISSION_STATE_LIMITED
    if allowed:
        return PERMISSION_STATE_ALLOWED
    return PERMISSION_STATE_DENIED


def permission_state_flags(state: str) -> tuple[bool, bool]:
    normalized = state if state in PERMISSION_STATE_CHOICES else PERMISSION_STATE_DENIED
    return normalized != PERMISSION_STATE_DENIED, normalized == PERMISSION_STATE_LIMITED


def sync_user_permission_fields_from_matrix(matrix_states: dict[str, str]) -> dict[str, bool]:
    def enabled(key: str) -> bool:
        return matrix_states.get(key, PERMISSION_STATE_DENIED) != PERMISSION_STATE_DENIED

    audit_enabled = enabled("security_audit.audit_data") or enabled("security_audit.view_logs")
    security_control_enabled = enabled("security_audit.security_control")
    block_users_enabled = enabled("security_audit.block_users")
    export_enabled = enabled("reports.export_reports")

    return {
        "user_create": enabled("user_management.create_users"),
        "user_read": enabled("user_management.view_users"),
        "user_update": enabled("user_management.edit_users") or enabled("user_management.assign_roles"),
        "user_delete": enabled("user_management.delete_users"),
        "user_lock": block_users_enabled,
        "user_unlock": block_users_enabled,
        "user_export": export_enabled,
        "user_reset_password": security_control_enabled,
        "user_audit_view": audit_enabled,
    }


def resolve_role_permission_matrix_states(role: str) -> dict[str, str]:
    if not role:
        return {}
    matrix = RolePermissionMatrix.objects.filter(role=role).first()
    stored_permissions = matrix.matrix_permissions if matrix else None
    return normalize_permission_matrix_states(role, stored_permissions)


def resolve_matrix_permission_state_for_role(role: str, permission_key: str) -> str:
    if not role or not permission_key:
        return PERMISSION_STATE_DENIED
    states = resolve_role_permission_matrix_states(role)
    return states.get(permission_key, PERMISSION_STATE_DENIED)


def resolve_matrix_permission_state_for_user(user, permission_key: str) -> str:
    if not getattr(user, "is_authenticated", False):
        return PERMISSION_STATE_DENIED
    if getattr(user, "is_superuser", False):
        return PERMISSION_STATE_ALLOWED
    return resolve_matrix_permission_state_for_role(getattr(user, "role", ""), permission_key)


def user_has_matrix_permission(user, permission_key: str, *, allow_limited: bool = True) -> bool:
    state = resolve_matrix_permission_state_for_user(user, permission_key)
    if state == PERMISSION_STATE_ALLOWED:
        return True
    if allow_limited and state == PERMISSION_STATE_LIMITED:
        return True
    return False


def user_has_any_matrix_permission(user, permission_keys, *, allow_limited: bool = True) -> bool:
    return any(user_has_matrix_permission(user, permission_key, allow_limited=allow_limited) for permission_key in permission_keys)


def build_permission_matrix_sections(matrices):
    role_labels = dict(User.ROLE_CHOICES)
    all_roles = [role for role, _label in User.ROLE_CHOICES]
    matrix_by_role = {}
    for matrix in matrices:
        matrix_by_role[matrix.role] = {
            "record": matrix,
            "states": normalize_permission_matrix_states(matrix.role, matrix.matrix_permissions),
        }

    sections = []
    for section in PERMISSION_MATRIX_SECTIONS:
        roles = [{"key": role, "label": role_labels.get(role, role.replace("_", " ").title())} for role in all_roles]
        rows = []
        for action in section["actions"]:
            permission_key = f"{section['key']}.{action['key']}"
            cells = []
            for role in all_roles:
                role_entry = matrix_by_role[role]
                state = role_entry["states"][permission_key]
                allowed, limited = permission_state_flags(state)
                cells.append(
                    {
                        "role": role,
                        "state": state,
                        "allowed": allowed,
                        "limited": limited,
                        "state_name": f"matrix_state__{role}__{section['key']}__{action['key']}",
                        "access_name": f"perm__{role}__{section['key']}__{action['key']}",
                        "scope_name": f"scope__{role}__{section['key']}__{action['key']}",
                    }
                )
            rows.append({"key": action["key"], "label": action["label"], "permission_key": permission_key, "cells": cells})
        sections.append(
            {
                "key": section["key"],
                "title": section["title"],
                "icon": section["icon"],
                "roles": roles,
                "rows": rows,
            }
        )
    return sections


def resolve_user_permissions(user) -> dict[str, bool]:
    role = getattr(user, "role", "")
    defaults = {
        "super_admin": {
            "create": True,
            "read": True,
            "update": True,
            "delete": True,
            "lock": True,
            "unlock": True,
            "export": True,
            "reset_password": True,
            "audit_view": True,
        },
        "admin": {
            "create": True,
            "read": True,
            "update": True,
            "delete": False,
            "lock": True,
            "unlock": True,
            "export": True,
            "reset_password": True,
            "audit_view": True,
        },
        "security_admin": {
            "create": True,
            "read": True,
            "update": True,
            "delete": False,
            "lock": True,
            "unlock": True,
            "export": True,
            "reset_password": True,
            "audit_view": True,
        },
        "operations_manager": {
            "create": True,
            "read": True,
            "update": True,
            "delete": False,
            "lock": True,
            "unlock": True,
            "export": True,
            "reset_password": False,
            "audit_view": True,
        },
        "procurement_manager": {
            "create": True,
            "read": True,
            "update": True,
            "delete": False,
            "lock": False,
            "unlock": False,
            "export": True,
            "reset_password": False,
            "audit_view": True,
        },
        "catalog_manager": {
            "create": True,
            "read": True,
            "update": True,
            "delete": False,
            "lock": False,
            "unlock": False,
            "export": True,
            "reset_password": False,
            "audit_view": True,
        },
        "compliance_officer": {
            "create": False,
            "read": True,
            "update": False,
            "delete": False,
            "lock": False,
            "unlock": False,
            "export": True,
            "reset_password": False,
            "audit_view": True,
        },
        "auditor": {
            "create": False,
            "read": True,
            "update": False,
            "delete": False,
            "lock": False,
            "unlock": False,
            "export": True,
            "reset_password": False,
            "audit_view": True,
        },
        "finance": {
            "create": False,
            "read": True,
            "update": False,
            "delete": False,
            "lock": False,
            "unlock": False,
            "export": True,
            "reset_password": False,
            "audit_view": True,
        },
        "support_agent": {
            "create": False,
            "read": True,
            "update": True,
            "delete": False,
            "lock": False,
            "unlock": False,
            "export": False,
            "reset_password": False,
            "audit_view": True,
        },
        "warehouse_operator": {
            "create": False,
            "read": True,
            "update": True,
            "delete": False,
            "lock": False,
            "unlock": False,
            "export": True,
            "reset_password": False,
            "audit_view": True,
        },
        "delivery_agent": {
            "create": False,
            "read": True,
            "update": False,
            "delete": False,
            "lock": False,
            "unlock": False,
            "export": False,
            "reset_password": False,
            "audit_view": False,
        },
        "doctor": {
            "create": False,
            "read": True,
            "update": False,
            "delete": False,
            "lock": False,
            "unlock": False,
            "export": False,
            "reset_password": False,
            "audit_view": False,
        },
        "marketing_manager": {
            "create": False,
            "read": True,
            "update": False,
            "delete": False,
            "lock": False,
            "unlock": False,
            "export": True,
            "reset_password": False,
            "audit_view": True,
        },
        "vendor_staff": {
            "create": False,
            "read": True,
            "update": False,
            "delete": False,
            "lock": False,
            "unlock": False,
            "export": False,
            "reset_password": False,
            "audit_view": False,
        },
        "manager": {
            "create": False,
            "read": True,
            "update": True,
            "delete": False,
            "lock": False,
            "unlock": False,
            "export": False,
            "reset_password": False,
            "audit_view": True,
        },
        "viewer": {
            "create": False,
            "read": True,
            "update": False,
            "delete": False,
            "lock": False,
            "unlock": False,
            "export": False,
            "reset_password": False,
            "audit_view": True,
        },
    }
    resolved = defaults.get(role, defaults["viewer"]).copy()
    matrix = RolePermissionMatrix.objects.filter(role=role).first()
    if matrix:
        for permission_name, field_name in USER_PERMISSION_FIELD_MAP.items():
            resolved[permission_name] = getattr(matrix, field_name)
    if getattr(user, "is_superuser", False):
        for key in resolved:
            resolved[key] = True
    return resolved


def ensure_role_permission_matrices():
    defaults: dict[str, dict[str, bool]] = {}
    for role, _label in User.ROLE_CHOICES:
        resolved = resolve_user_permissions(type("RoleStub", (), {"role": role, "is_superuser": False})())
        defaults[role] = {
            "user_create": resolved["create"],
            "user_read": resolved["read"],
            "user_update": resolved["update"],
            "user_delete": resolved["delete"],
            "user_lock": resolved["lock"],
            "user_unlock": resolved["unlock"],
            "user_export": resolved["export"],
            "user_reset_password": resolved["reset_password"],
            "user_audit_view": resolved["audit_view"],
        }
    for role, values in defaults.items():
        matrix, created = RolePermissionMatrix.objects.get_or_create(
            role=role,
            defaults={**values, "matrix_permissions": build_default_permission_matrix_states(role)},
        )
        normalized_states = normalize_permission_matrix_states(role, matrix.matrix_permissions)
        synced_values = sync_user_permission_fields_from_matrix(normalized_states)
        update_fields = []
        if matrix.matrix_permissions != normalized_states:
            matrix.matrix_permissions = normalized_states
            update_fields.append("matrix_permissions")
        for field_name, field_value in synced_values.items():
            if getattr(matrix, field_name) != field_value:
                setattr(matrix, field_name, field_value)
                update_fields.append(field_name)
        if not created and update_fields:
            matrix.save(update_fields=update_fields + ["updated_at"])


class HasUserPermission(BasePermission):
    required_permission = "read"

    def has_permission(self, request, view):
        user = request.user
        if not bool(user and user.is_authenticated):
            return False
        required = getattr(view, "required_user_permission", self.required_permission)
        return resolve_user_permissions(user).get(required, False)


class HasMatrixPermission(BasePermission):
    message = "You do not have permission for this action."

    def has_permission(self, request, view):
        user = request.user
        if not bool(user and user.is_authenticated):
            return False

        required = getattr(view, "required_matrix_permission", None)
        permission_map = getattr(view, "matrix_permission_map", None)
        allow_limited = getattr(view, "allow_limited_matrix_permission", True)

        if isinstance(permission_map, dict):
            required = permission_map.get(request.method, required)

        if required in (None, "", []):
            return True

        if isinstance(required, (list, tuple, set)):
            return user_has_any_matrix_permission(user, required, allow_limited=allow_limited)

        return user_has_matrix_permission(user, required, allow_limited=allow_limited)


def _admin_user_queryset():
    return User.objects.select_related("created_by", "updated_by", "deleted_by").order_by("-created_at")


def _apply_admin_user_filters(queryset, params):
    query = (params.get("q") or "").strip()
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
        value = (params.get(field_name) or "").strip()
        if value:
            queryset = queryset.filter(**{field_name: value})
    status_value = (params.get("status") or "").strip()
    if status_value:
        queryset = queryset.filter(account_status=status_value)
    if params.get("email_verified") in {"true", "false"}:
        queryset = queryset.filter(email_verified=params.get("email_verified") == "true")
    if params.get("account_locked") in {"true", "false"}:
        queryset = queryset.filter(account_locked=params.get("account_locked") == "true")
    try:
        active_min_minutes = int((params.get("active_min_minutes") or "").strip())
    except ValueError:
        active_min_minutes = None
    try:
        active_max_minutes = int((params.get("active_max_minutes") or "").strip())
    except ValueError:
        active_max_minutes = None
    if active_min_minutes is not None and active_min_minutes >= 0:
        queryset = queryset.filter(customer_active_seconds_total__gte=active_min_minutes * 60)
    if active_max_minutes is not None and active_max_minutes >= 0:
        queryset = queryset.filter(customer_active_seconds_total__lte=active_max_minutes * 60)
    return queryset


def _export_users_excel_xml(queryset):
    users = list(queryset)
    today = timezone.localdate()
    week_start = today - timezone.timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    activity_rows = (
        CustomerWebsiteActivityDaily.objects.filter(user_id__in=[user.pk for user in users], activity_date__gte=month_start)
        .values("user_id")
        .annotate(
            month_seconds=Sum("active_seconds"),
            week_seconds=Sum("active_seconds", filter=Q(activity_date__gte=week_start)),
            today_seconds=Sum("active_seconds", filter=Q(activity_date=today)),
        )
    )
    activity_by_user = {row["user_id"]: row for row in activity_rows}
    rows = []
    for user in users:
        activity = activity_by_user.get(user.pk, {})
        rows.append(
            [
                str(user.pk),
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
                format_active_duration(activity.get("today_seconds") or 0),
                format_active_duration(activity.get("week_seconds") or 0),
                format_active_duration(activity.get("month_seconds") or 0),
                user.get_account_status_display(),
                "Yes" if user.email_verified else "No",
                "Yes" if user.account_locked else "No",
                "Yes" if user.mfa_enabled else "No",
                str(user.failed_login_attempts),
                timezone.localtime(user.last_login).strftime("%d %b %Y, %H:%M") if user.last_login else "",
                user.last_login_ip or "",
            ]
        )
    headers = [
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
    ]
    def cell(value):
        safe = str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f'<Cell><Data ss:Type="String">{safe}</Data></Cell>'
    xml_rows = [f"<Row>{''.join(cell(header) for header in headers)}</Row>"]
    xml_rows.extend(f"<Row>{''.join(cell(item) for item in row)}</Row>" for row in rows)
    payload = f"""<?xml version="1.0"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:x="urn:schemas-microsoft-com:office:excel"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
 <Worksheet ss:Name="Users">
  <Table>
   {''.join(xml_rows)}
  </Table>
 </Worksheet>
</Workbook>"""
    response = HttpResponse(payload, content_type="application/vnd.ms-excel")
    response["Content-Disposition"] = 'attachment; filename="users-export.xls"'
    return response


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AuthSendOtpThrottle])
def send_otp(request):
    serializer = SendOTPSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    phone_number = serializer.validated_data["phone_number"].strip()
    purpose = serializer.validated_data["purpose"]

    otp_request = OTPRequest.objects.create(
        phone_number=phone_number,
        purpose=purpose,
        otp_code=_generate_otp_code(),
        expires_at=OTPRequest.default_expiry(),
    )

    payload = {
        "status": "otp_sent",
        "phone_number": phone_number,
        "purpose": purpose,
        "expires_at": otp_request.expires_at,
    }
    if settings.DEBUG and getattr(settings, "EXPOSE_DEBUG_OTP_CODE", False):
        payload["otp_code"] = otp_request.otp_code

    return Response(payload, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AuthVerifyOtpThrottle])
@transaction.atomic
def verify_otp(request):
    serializer = VerifyOTPSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    phone_number = serializer.validated_data["phone_number"].strip()
    otp_code = serializer.validated_data["otp_code"]
    purpose = serializer.validated_data["purpose"]

    otp_request = (
        OTPRequest.objects.select_for_update()
        .filter(phone_number=phone_number, purpose=purpose, verified_at__isnull=True)
        .order_by("-created_at")
        .first()
    )

    if not otp_request:
        return Response({"detail": "No active OTP request found."}, status=status.HTTP_400_BAD_REQUEST)

    if otp_request.attempt_count >= settings.OTP_MAX_ATTEMPTS:
        return Response(
            {"detail": "Too many invalid OTP attempts. Please request a new OTP."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    if otp_request.is_expired:
        return Response({"detail": "OTP has expired."}, status=status.HTTP_400_BAD_REQUEST)

    if otp_request.otp_code != otp_code:
        otp_request.attempt_count += 1
        otp_request.save(update_fields=["attempt_count"])
        return Response({"detail": "Invalid OTP code."}, status=status.HTTP_400_BAD_REQUEST)

    otp_request.verified_at = timezone.now()
    otp_request.save(update_fields=["verified_at"])

    user_defaults = {
        "full_name": serializer.validated_data.get("full_name", ""),
        "is_phone_verified": True,
        "role": "customer",
        "type_of_user": "customer",
        "account_status": "active",
        "approval_status": "approved",
    }
    email = serializer.validated_data.get("email")
    if email:
        user_defaults["email"] = email

    user, created = User.objects.get_or_create(phone_number=phone_number, defaults=user_defaults)
    if not created:
        updated_fields: list[str] = []
        if not user.is_phone_verified:
            user.is_phone_verified = True
            updated_fields.append("is_phone_verified")
        if not user.created_by_id:
            user.created_by = user
            updated_fields.append("created_by")
        if not user.updated_by_id:
            user.updated_by = user
            updated_fields.append("updated_by")
        if updated_fields:
            updated_fields.append("updated_at")
            user.save(update_fields=updated_fields)
    else:
        update_fields: list[str] = []
        if not user.created_by_id:
            user.created_by = user
            update_fields.append("created_by")
        if not user.updated_by_id:
            user.updated_by = user
            update_fields.append("updated_by")
        if update_fields:
            update_fields.append("updated_at")
            user.save(update_fields=update_fields)

    if purpose == "login" and user.role not in PUBLIC_OTP_LOGIN_ALLOWED_ROLES:
        return Response(
            {"detail": "OTP login is only available for customer accounts."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if user.approval_status != "approved":
        return Response({"detail": f"Account approval is {user.approval_status}."}, status=status.HTTP_403_FORBIDDEN)

    if not user.can_sign_in:
        return Response({"detail": f"Account is {user.account_status}."}, status=status.HTTP_403_FORBIDDEN)

    if user.force_password_reset or user.password_expired:
        return Response({"detail": "Password reset required before continuing."}, status=status.HTTP_403_FORBIDDEN)

    Token.objects.filter(user=user).delete()
    token = Token.objects.create(user=user)
    user.last_login = timezone.now()
    user.last_login_ip = _request_ip(request)
    user.save(update_fields=["last_login", "last_login_ip", "updated_at"])
    session_expires_at = _token_expiry_for(token)

    record_audit_event(
        actor=user,
        event_type="auth_login_verified",
        entity_type="user",
        entity_id=user.id,
        message=f"OTP login verified for {user.phone_number}.",
        meta={"purpose": purpose, "session_expires_at": session_expires_at.isoformat() if session_expires_at else ""},
    )

    return Response(
        {
            "status": "verified",
            "token": token.key,
            "expires_at": session_expires_at,
            "user": UserSerializer(user, context={"session_expires_at": session_expires_at}).data,
        }
    )


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def me(request):
    if not user_has_matrix_permission(request.user, "core_access.profile_own"):
        return Response({"detail": "You do not have permission to access your profile."}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "GET":
        session_expires_at = _token_expiry_for(request.auth)
        return Response(UserSerializer(request.user, context={"session_expires_at": session_expires_at}).data)

    serializer = UserProfileUpdateSerializer(request.user, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    session_expires_at = _token_expiry_for(request.auth)
    return Response(UserSerializer(request.user, context={"session_expires_at": session_expires_at}).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    if request.auth:
        request.auth.delete()

    record_audit_event(
        actor=request.user,
        event_type="auth_logout",
        entity_type="user",
        entity_id=request.user.id,
        message=f"Session revoked for {request.user.phone_number}.",
    )
    return Response({"status": "logged_out"}, status=status.HTTP_200_OK)


class CustomerWebsiteActivityHeartbeatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != "customer":
            return Response({"status": "ignored", "reason": "not_customer"}, status=status.HTTP_200_OK)

        tab_id = (request.data.get("tab_id") or "").strip()
        if not CUSTOMER_ACTIVITY_TAB_ID_RE.match(tab_id):
            return Response({"detail": "Invalid activity tab id."}, status=status.HTTP_400_BAD_REQUEST)

        payload = _record_customer_activity_heartbeat(request.user, tab_id=tab_id)
        return Response(payload, status=status.HTTP_200_OK)


class MyAddressListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasMatrixPermission]
    required_matrix_permission = "settings.personal_settings"
    serializer_class = CustomerAddressSerializer

    def get_queryset(self):
        return CustomerAddress.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        is_default = serializer.validated_data.get("is_default", False)
        if is_default or not CustomerAddress.objects.filter(user=self.request.user).exists():
            CustomerAddress.objects.filter(user=self.request.user, is_default=True).update(is_default=False)
            serializer.save(user=self.request.user, is_default=True)
            return
        serializer.save(user=self.request.user)


class MyAddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasMatrixPermission]
    required_matrix_permission = "settings.personal_settings"
    serializer_class = CustomerAddressSerializer

    def get_queryset(self):
        return CustomerAddress.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        is_default = serializer.validated_data.get("is_default", False)
        if is_default:
            CustomerAddress.objects.filter(user=self.request.user, is_default=True).exclude(
                pk=serializer.instance.pk
            ).update(is_default=False)
        serializer.save()


class MyPaymentMethodListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasMatrixPermission]
    required_matrix_permission = "settings.personal_settings"
    serializer_class = SavedPaymentMethodSerializer

    def get_queryset(self):
        return SavedPaymentMethod.objects.filter(user=self.request.user, is_active=True)

    def perform_create(self, serializer):
        is_default = serializer.validated_data.get("is_default", False)
        if is_default or not SavedPaymentMethod.objects.filter(user=self.request.user, is_active=True).exists():
            SavedPaymentMethod.objects.filter(user=self.request.user, is_default=True).update(is_default=False)
            serializer.save(user=self.request.user, is_default=True)
            return
        serializer.save(user=self.request.user)


class MyPaymentMethodDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasMatrixPermission]
    required_matrix_permission = "settings.personal_settings"
    serializer_class = SavedPaymentMethodSerializer

    def get_queryset(self):
        return SavedPaymentMethod.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        is_default = serializer.validated_data.get("is_default", False)
        if is_default:
            SavedPaymentMethod.objects.filter(user=self.request.user, is_default=True).exclude(
                pk=serializer.instance.pk
            ).update(is_default=False)
        serializer.save()

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.is_default = False
        instance.save(update_fields=["is_active", "is_default", "updated_at"])


class AdminUserListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasUserPermission]
    required_user_permission = "read"
    serializer_class = AdminUserManagementSerializer

    def get_queryset(self):
        queryset = _apply_admin_user_filters(_admin_user_queryset(), self.request.query_params)
        sort = self.request.query_params.get("sort") or "-created_at"
        if sort.lstrip("-") in {
            "id", "employee_code", "full_name", "username", "role", "department", "designation",
            "email", "phone_number", "country", "state", "district", "account_status",
            "email_verified", "account_locked", "last_login", "created_at", "updated_at",
            "customer_active_seconds_total",
        }:
            queryset = queryset.order_by(sort)
        return queryset

    def get_permissions(self):
        if self.request.method == "POST":
            self.required_user_permission = "create"
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data,
            context={
                "request": request,
                "temporary_password": (request.data.get("temporary_password") or "").strip(),
                "invite_user": request.data.get("invite_user") in {True, "true", "1", "on"},
            },
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        record_audit_event(
            actor=request.user,
            event_type="user_created",
            entity_type="user",
            entity_id=user.pk,
            message=f"API created user {user.full_name or user.phone_number}.",
        )
        return Response(self.get_serializer(user).data, status=status.HTTP_201_CREATED)


class AdminUserEmployeeCodeGenerateView(APIView):
    permission_classes = [IsAuthenticated, HasUserPermission]
    required_user_permission = "create"

    def get(self, request):
        role = (request.query_params.get("role") or "").strip()
        if not role or role not in User.ROLE_CHOICES_DICT:
            return Response({"detail": "Select a valid role first."}, status=status.HTTP_400_BAD_REQUEST)
        employee_code = User.generate_unique_employee_code(role)
        return Response({"role": role, "prefix": User.get_employee_code_prefix(role), "employee_code": employee_code})


class AdminUsernameGenerateView(APIView):
    permission_classes = [IsAuthenticated, HasUserPermission]
    required_user_permission = "create"

    def get(self, request):
        full_name = (request.query_params.get("full_name") or "").strip()
        email = (request.query_params.get("email") or "").strip()
        phone_number = (request.query_params.get("phone_number") or "").strip()
        if not full_name and not email and not phone_number:
            return Response({"detail": "Enter a name, email, or phone number first."}, status=status.HTTP_400_BAD_REQUEST)
        username = User.generate_unique_username(full_name, email, phone_number)
        return Response({"username": username})


class AdminUserEmployeeCodeLookupView(APIView):
    permission_classes = [IsAuthenticated, HasUserPermission]
    required_user_permission = "read"

    def get(self, request):
        employee_code = (request.query_params.get("employee_code") or "").strip().upper()
        user_id = (request.query_params.get("user_id") or "").strip()
        if not employee_code and not user_id:
            return Response({"detail": "Enter a User ID or Employee Code."}, status=status.HTTP_400_BAD_REQUEST)

        users = _admin_user_queryset()
        user = None
        if user_id:
            if not user_id.isdigit():
                return Response({"detail": "User ID must be numeric."}, status=status.HTTP_400_BAD_REQUEST)
            user = users.filter(pk=int(user_id)).first()

        if not user and employee_code:
            code_filters = Q(employee_code__iexact=employee_code)
            numeric_code = re.sub(r"\D", "", employee_code)
            if numeric_code and numeric_code == employee_code:
                code_filters |= Q(employee_code__iendswith=f"-{numeric_code}")
            user = users.filter(code_filters).first()

        if not user:
            return Response({"detail": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(_serialize_admin_user_lookup(user))


class AdminUserLocationOptionsView(APIView):
    permission_classes = [IsAuthenticated, HasUserPermission]
    required_user_permission = "read"

    def get(self, request):
        country = (request.query_params.get("country") or "").strip()
        state = (request.query_params.get("state") or "").strip()
        countries = [entry["name"] for entry in get_all_countries()]
        states = get_states_of_country(country) if country else []
        districts = get_districts_of_state(country, state) if country and state else []
        return Response(
            {
                "countries": countries,
                "states": states,
                "districts": districts,
            }
        )


class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasUserPermission]
    serializer_class = AdminUserManagementSerializer
    queryset = _admin_user_queryset()

    def get_permissions(self):
        if self.request.method in {"PATCH", "PUT"}:
            self.required_user_permission = "update"
        elif self.request.method == "DELETE":
            self.required_user_permission = "delete"
        else:
            self.required_user_permission = "read"
        return super().get_permissions()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=True,
            context={"request": request, "temporary_password": (request.data.get("temporary_password") or "").strip()},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        record_audit_event(
            actor=request.user,
            event_type="user_updated",
            entity_type="user",
            entity_id=user.pk,
            message=f"API updated user {user.full_name or user.phone_number}.",
        )
        return Response(self.get_serializer(user).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.account_status = "deleted"
        instance.deleted_at = timezone.now()
        instance.deleted_by = request.user
        instance.updated_by = request.user
        instance.save(update_fields=["account_status", "deleted_at", "deleted_by", "updated_by", "updated_at", "is_active"])
        record_audit_event(
            actor=request.user,
            event_type="user_deleted",
            entity_type="user",
            entity_id=instance.pk,
            severity="warning",
            message=f"API soft deleted user {instance.full_name or instance.phone_number}.",
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminUserBulkActionView(APIView):
    permission_classes = [IsAuthenticated, HasUserPermission]
    required_user_permission = "update"

    def get_permissions(self):
        action = (self.request.data.get("action") or "").strip() if hasattr(self.request, "data") else ""
        self.required_user_permission = "export" if action == "export" else "update"
        return super().get_permissions()

    def post(self, request):
        action = (request.data.get("action") or "").strip()
        ids = request.data.get("user_ids") or []
        queryset = _admin_user_queryset().filter(pk__in=ids)
        if not queryset.exists():
            return Response({"detail": "No matching users selected."}, status=status.HTTP_400_BAD_REQUEST)
        if action == "export":
            return _export_users_excel_xml(queryset)
        for user in queryset:
            if action == "activate":
                user.account_status = "active"
            elif action == "deactivate":
                user.account_status = "inactive"
            elif action == "lock":
                user.account_locked = True
            elif action == "unlock":
                user.account_locked = False
                user.failed_login_attempts = 0
            elif action == "soft_delete":
                user.account_status = "deleted"
                user.deleted_at = timezone.now()
                user.deleted_by = request.user
            else:
                return Response({"detail": "Unsupported bulk action."}, status=status.HTTP_400_BAD_REQUEST)
            user.updated_by = request.user
            user.save()
        record_audit_event(
            actor=request.user,
            event_type="user_bulk_action",
            entity_type="user",
            message=f"API bulk action '{action}' executed for {queryset.count()} users.",
            meta={"action": action, "count": queryset.count()},
        )
        return Response({"status": "ok", "count": queryset.count()})


class AdminUserResetPasswordView(APIView):
    permission_classes = [IsAuthenticated, HasUserPermission]
    required_user_permission = "reset_password"

    def post(self, request, pk):
        user = generics.get_object_or_404(_admin_user_queryset(), pk=pk)
        try:
            send_user_password_reset_link(user, request=request, initiated_by=request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        record_audit_event(
            actor=request.user,
            event_type="user_password_reset",
            entity_type="user",
            entity_id=user.pk,
            severity="warning",
            message=f"API password reset link issued for {user.full_name or user.phone_number}.",
        )
        return Response({"reset_link_sent": True})


class AdminUserLockToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, action):
        action = (action or "").strip().lower()
        if action not in {"lock", "unlock"}:
            return Response({"detail": "Unsupported lock action."}, status=status.HTTP_400_BAD_REQUEST)
        permissions = resolve_user_permissions(request.user)
        required = "lock" if action == "lock" else "unlock"
        if not permissions.get(required, False):
            return Response({"detail": "You do not have permission for this action."}, status=status.HTTP_403_FORBIDDEN)
        user = generics.get_object_or_404(_admin_user_queryset(), pk=pk)
        user.account_locked = action == "lock"
        if action == "unlock":
            user.failed_login_attempts = 0
        user.updated_by = request.user
        user.save(update_fields=["account_locked", "failed_login_attempts", "updated_by", "updated_at"])
        record_audit_event(
            actor=request.user,
            event_type=f"user_{action}",
            entity_type="user",
            entity_id=user.pk,
            severity="warning" if action == "lock" else "info",
            message=f"API {action}ed {user.full_name or user.phone_number}.",
        )
        return Response({"status": action, "account_locked": user.account_locked})


class AdminUserExportView(APIView):
    permission_classes = [IsAuthenticated, HasUserPermission]
    required_user_permission = "export"

    def get(self, request):
        queryset = _apply_admin_user_filters(_admin_user_queryset(), request.query_params)
        format_name = (request.GET.get("format") or "csv").lower()
        if format_name == "xls":
            return _export_users_excel_xml(queryset)
        users = list(queryset)
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="users-export.csv"'
        writer = csv.writer(response)
        writer.writerow(["User ID", "Employee Code", "Full Name", "Username", "Role", "Department", "Email", "Customer Active Hrs in Website", "Status"])
        for user in users:
            writer.writerow([user.pk, user.employee_code or "", user.full_name or "", user.username or "", user.role, user.department or "", user.email or "", user.customer_active_duration_label, user.account_status])
        return response


class AdminUserAuditView(APIView):
    permission_classes = [IsAuthenticated, HasUserPermission]
    required_user_permission = "audit_view"

    def get(self, request, pk):
        from platform_apps.audit.models import AuditLog

        records = AuditLog.objects.filter(entity_type="user", entity_id=str(pk)).order_by("-created_at")[:50]
        data = [
            {
                "event_type": record.event_type,
                "message": record.message,
                "severity": record.severity,
                "actor_label": record.actor_label,
                "created_at": record.created_at,
                "meta": record.meta,
            }
            for record in records
        ]
        return Response({"results": data})


class UserSavedFilterViewListCreateAPI(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasUserPermission]
    required_user_permission = "read"
    serializer_class = UserSavedFilterViewSerializer

    def get_queryset(self):
        return UserSavedFilterView.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        if serializer.validated_data.get("is_default"):
            UserSavedFilterView.objects.filter(owner=self.request.user, is_default=True).update(is_default=False)
        serializer.save(owner=self.request.user)


class UserSavedFilterViewDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasUserPermission]
    required_user_permission = "read"
    serializer_class = UserSavedFilterViewSerializer

    def get_queryset(self):
        return UserSavedFilterView.objects.filter(owner=self.request.user)

    def perform_update(self, serializer):
        if serializer.validated_data.get("is_default"):
            UserSavedFilterView.objects.filter(owner=self.request.user, is_default=True).exclude(pk=serializer.instance.pk).update(is_default=False)
        serializer.save()


class RolePermissionMatrixListUpdateAPI(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasUserPermission]
    required_user_permission = "audit_view"
    serializer_class = RolePermissionMatrixSerializer

    def get_queryset(self):
        ensure_role_permission_matrices()
        return RolePermissionMatrix.objects.all().order_by("role")


class RolePermissionMatrixDetailAPI(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated, HasUserPermission]
    required_user_permission = "audit_view"
    serializer_class = RolePermissionMatrixSerializer

    def get_queryset(self):
        ensure_role_permission_matrices()
        return RolePermissionMatrix.objects.all()


class AdminUserActivityReportView(APIView):
    permission_classes = [IsAuthenticated, HasUserPermission]
    required_user_permission = "export"

    def get(self, request):
        queryset = _apply_admin_user_filters(_admin_user_queryset(), request.query_params)
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="user-activity-report.csv"'
        writer = csv.writer(response)
        writer.writerow(["User ID", "Full Name", "Status", "Last Login", "Last Login IP", "Failed Login Attempts", "Password Last Changed", "Password Expired"])
        for user in queryset:
            writer.writerow([
                user.pk,
                user.full_name or user.phone_number,
                user.account_status,
                timezone.localtime(user.last_login).strftime("%d %b %Y, %H:%M") if user.last_login else "",
                user.last_login_ip or "",
                user.failed_login_attempts,
                timezone.localtime(user.password_last_changed_at).strftime("%d %b %Y, %H:%M") if user.password_last_changed_at else "",
                "Yes" if user.password_expired else "No",
            ])
        return response


class AdminUserAuditReportView(APIView):
    permission_classes = [IsAuthenticated, HasUserPermission]
    required_user_permission = "audit_view"

    def get(self, request):
        from platform_apps.audit.models import AuditLog

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="user-audit-report.csv"'
        writer = csv.writer(response)
        writer.writerow(["When", "Event Type", "Severity", "Entity ID", "Actor", "Message"])
        for record in AuditLog.objects.filter(entity_type="user").order_by("-created_at")[:500]:
            writer.writerow([
                timezone.localtime(record.created_at).strftime("%d %b %Y, %H:%M"),
                record.event_type,
                record.severity,
                record.entity_id,
                record.actor_label,
                record.message,
            ])
        return response
