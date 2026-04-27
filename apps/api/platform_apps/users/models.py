from datetime import timedelta
import secrets
import re
import unicodedata

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from .managers import UserManager


def approval_document_upload_to(instance, filename: str) -> str:
    role = getattr(instance, "role", "general") or "general"
    return f"approval-documents/{role}/{filename}"


def format_active_duration(total_seconds: int | None) -> str:
    seconds = max(0, int(total_seconds or 0))
    hours, remainder = divmod(seconds, 3600)
    minutes, remaining_seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_EMPLOYEE_CODE_PREFIXES = {
        "customer": "CUS",
        "vendor": "VND",
        "vendor_staff": "VST",
        "pharmacist": "PHR",
        "doctor": "DOC",
        "warehouse_operator": "WHO",
        "delivery_agent": "DLY",
        "procurement_manager": "PRC",
        "operations_manager": "OPS",
        "support_agent": "SUP",
        "finance": "FIN",
        "catalog_manager": "CAT",
        "marketing_manager": "MKT",
        "admin": "ADM",
        "compliance_officer": "COM",
        "auditor": "AUD",
        "viewer": "VIW",
        "security_admin": "SEC",
        "super_admin": "SAD",
    }
    ROLE_CHOICES = (
        ("customer", "Customer"),
        ("vendor", "Vendor"),
        ("pharmacist", "Pharmacist"),
        ("admin", "Admin"),
        ("super_admin", "Super Admin"),
        ("warehouse_operator", "Warehouse Operator"),
        ("delivery_agent", "Delivery Agent"),
        ("support_agent", "Support Agent"),
        ("finance", "Finance"),
        ("catalog_manager", "Catalog Manager"),
        ("operations_manager", "Operations Manager"),
        ("procurement_manager", "Procurement Manager"),
        ("compliance_officer", "Compliance Officer"),
        ("security_admin", "Security Admin"),
        ("auditor", "Auditor"),
        ("doctor", "Doctor"),
        ("marketing_manager", "Marketing Manager"),
        ("vendor_staff", "Vendor Staff"),
        ("viewer", "Viewer"),
    )
    ROLE_CHOICES_DICT = dict(ROLE_CHOICES)
    ACCOUNT_STATUS_CHOICES = (
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("blocked", "Blocked"),
        ("suspended", "Suspended"),
        ("deleted", "Deleted"),
    )
    TYPE_OF_USER_CHOICES = (
        ("employee", "Employee"),
        ("partner", "Partner"),
        ("customer", "Customer"),
        ("system", "System"),
    )
    APPROVAL_STATUS_CHOICES = (
        ("approved", "Approved"),
        ("pending", "Pending Approval"),
        ("rejected", "Rejected"),
    )
    DOCUMENT_REVIEW_STATUS_CHOICES = (
        ("not_required", "Not Required"),
        ("pending", "Pending Review"),
        ("verified", "Verified"),
        ("rejected", "Rejected"),
    )
    APPROVAL_SPECIALTY_CHOICES = (
        ("all", "All Approval Types"),
        ("vendor", "Vendor Reviews"),
        ("pharmacist", "Pharmacist Reviews"),
    )

    phone_number = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True, null=True, unique=True)
    username = models.CharField(max_length=80, blank=True, null=True, unique=True)
    employee_code = models.CharField(max_length=80, blank=True, null=True, unique=True)
    full_name = models.CharField(max_length=255, blank=True)
    type_of_user = models.CharField(max_length=24, choices=TYPE_OF_USER_CHOICES, default="employee")
    department = models.CharField(max_length=120, blank=True)
    designation = models.CharField(max_length=120, blank=True)
    business_name = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=120, blank=True)
    district = models.CharField(max_length=120, blank=True)
    address = models.TextField(blank=True)
    vendor_license_number = models.CharField(max_length=120, blank=True)
    vendor_license_document = models.FileField(upload_to=approval_document_upload_to, blank=True)
    vendor_license_document_status = models.CharField(max_length=16, choices=DOCUMENT_REVIEW_STATUS_CHOICES, default="not_required")
    pharmacist_registration_number = models.CharField(max_length=120, blank=True)
    pharmacist_registration_document = models.FileField(upload_to=approval_document_upload_to, blank=True)
    pharmacist_registration_document_status = models.CharField(max_length=16, choices=DOCUMENT_REVIEW_STATUS_CHOICES, default="not_required")
    role = models.CharField(max_length=32, choices=ROLE_CHOICES, default="customer")
    account_status = models.CharField(max_length=16, choices=ACCOUNT_STATUS_CHOICES, default="active")
    approval_status = models.CharField(max_length=16, choices=APPROVAL_STATUS_CHOICES, default="approved")
    approval_notes = models.TextField(blank=True)
    approval_specialty = models.CharField(max_length=16, choices=APPROVAL_SPECIALTY_CHOICES, default="all")
    approval_available_for_assignment = models.BooleanField(default=True)
    approval_unavailable_until = models.DateTimeField(blank=True, null=True)
    approval_shift_start_hour = models.PositiveSmallIntegerField(default=9)
    approval_shift_end_hour = models.PositiveSmallIntegerField(default=18)
    approval_shift_weekdays = models.CharField(max_length=32, default="0,1,2,3,4,5,6")
    approval_leave_dates = models.CharField(max_length=255, blank=True)
    approval_assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_user_approvals",
    )
    approval_assigned_at = models.DateTimeField(blank=True, null=True)
    approval_due_at = models.DateTimeField(blank=True, null=True)
    approval_last_escalated_at = models.DateTimeField(blank=True, null=True)
    approval_reviewed_at = models.DateTimeField(blank=True, null=True)
    approval_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_user_approvals",
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    account_locked = models.BooleanField(default=False)
    mfa_enabled = models.BooleanField(default=False)
    force_password_reset = models.BooleanField(default=False)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    password_last_changed_at = models.DateTimeField(blank=True, null=True)
    customer_active_seconds_total = models.PositiveBigIntegerField(default=0)
    customer_activity_active_tab_id = models.CharField(max_length=64, blank=True)
    customer_activity_active_tab_seen_at = models.DateTimeField(blank=True, null=True)
    remarks = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_users",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="updated_users",
    )
    deleted_at = models.DateTimeField(blank=True, null=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deleted_users",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.full_name or self.email or self.phone_number

    @classmethod
    def get_employee_code_prefix(cls, role: str) -> str:
        return cls.ROLE_EMPLOYEE_CODE_PREFIXES.get(role or "", "USR")

    @classmethod
    def generate_employee_code_candidate(cls, role: str) -> str:
        prefix = cls.get_employee_code_prefix(role)
        random_number = 10_000_000 + secrets.randbelow(90_000_000)
        return f"{prefix}-{random_number}"

    @classmethod
    def generate_unique_employee_code(cls, role: str) -> str:
        for _attempt in range(50):
            candidate = cls.generate_employee_code_candidate(role)
            if not cls.objects.filter(employee_code__iexact=candidate).exists():
                return candidate
        raise RuntimeError("Could not generate a unique employee code.")

    @staticmethod
    def normalize_username_candidate(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value or "")
        ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
        ascii_only = ascii_only.lower().strip()
        parts = [re.sub(r"[^a-z0-9]+", "", part) for part in ascii_only.split()]
        parts = [part for part in parts if part]
        if len(parts) >= 2:
            candidate = ".".join(parts[:2])
        elif parts:
            candidate = parts[0]
        else:
            compact = re.sub(r"[^a-z0-9]+", "", ascii_only)
            candidate = compact or "user"
        return candidate[:80].strip(".") or "user"

    @classmethod
    def generate_unique_username(cls, *parts: str) -> str:
        base_source = " ".join(part.strip() for part in parts if part and part.strip())
        base_candidate = cls.normalize_username_candidate(base_source)
        if not cls.objects.filter(username__iexact=base_candidate).exists():
            return base_candidate
        for suffix in range(2, 1000):
            candidate = f"{base_candidate}{suffix}"
            if not cls.objects.filter(username__iexact=candidate).exists():
                return candidate
        for _attempt in range(50):
            candidate = f"{base_candidate}{10 + secrets.randbelow(90)}"
            if not cls.objects.filter(username__iexact=candidate).exists():
                return candidate
        raise RuntimeError("Could not generate a unique username.")

    @property
    def is_super_admin(self) -> bool:
        return self.role == "super_admin" or self.is_superuser

    @property
    def requires_approval(self) -> bool:
        return self.role in {"pharmacist", "vendor"}

    @property
    def can_sign_in(self) -> bool:
        return (
            self.is_active
            and self.account_status == "active"
            and not self.account_locked
            and self.deleted_at is None
            and self.approval_status == "approved"
        )

    @property
    def is_deleted(self) -> bool:
        return self.account_status == "deleted" or self.deleted_at is not None

    @property
    def documents_ready_for_approval(self) -> bool:
        if self.role == "vendor":
            return self.vendor_license_document_status == "verified"
        if self.role == "pharmacist":
            return self.pharmacist_registration_document_status == "verified"
        return True

    @property
    def approval_is_overdue(self) -> bool:
        return self.approval_status == "pending" and bool(self.approval_due_at and timezone.now() > self.approval_due_at)

    @property
    def approval_sla_state(self) -> str:
        if self.approval_status != "pending":
            return "resolved"
        if self.approval_is_overdue:
            return "overdue"
        return "on_track"

    def can_review_approval_role(self, approval_role: str) -> bool:
        return self.approval_specialty == "all" or self.approval_specialty == approval_role

    @property
    def password_expired(self) -> bool:
        if self.password_last_changed_at is None:
            return False
        return self.password_last_changed_at < timezone.now() - timezone.timedelta(days=90)

    @property
    def customer_active_duration_label(self) -> str:
        return format_active_duration(self.customer_active_seconds_total)

    @property
    def approval_shift_weekday_list(self) -> list[int]:
        weekdays: list[int] = []
        for value in (self.approval_shift_weekdays or "").split(","):
            value = value.strip()
            if not value:
                continue
            try:
                weekday = int(value)
            except ValueError:
                continue
            if 0 <= weekday <= 6:
                weekdays.append(weekday)
        return sorted(set(weekdays))

    @property
    def approval_leave_date_list(self) -> list:
        leave_dates = []
        for value in (self.approval_leave_dates or "").split(","):
            value = value.strip()
            if not value:
                continue
            try:
                leave_dates.append(timezone.datetime.fromisoformat(value).date())
            except ValueError:
                continue
        return sorted(set(leave_dates))

    def is_within_approval_shift(self, at_time=None) -> bool:
        current_time = timezone.localtime(at_time or timezone.now())
        weekdays = self.approval_shift_weekday_list
        if weekdays and current_time.weekday() not in weekdays:
            return False
        if current_time.date() in self.approval_leave_date_list:
            return False

        start_hour = max(0, min(23, self.approval_shift_start_hour))
        end_hour = max(0, min(23, self.approval_shift_end_hour))
        current_hour = current_time.hour

        if start_hour == end_hour:
            return True
        if start_hour < end_hour:
            return start_hour <= current_hour <= end_hour
        return current_hour >= start_hour or current_hour <= end_hour

    @property
    def is_available_for_approval_assignment(self) -> bool:
        if not self.approval_available_for_assignment:
            return False
        if self.approval_unavailable_until and self.approval_unavailable_until > timezone.now():
            return False
        return self.is_within_approval_shift()

    def save(self, *args, **kwargs):
        if self.role == "super_admin":
            self.is_staff = True
            self.is_superuser = True
        elif self.role == "admin":
            self.is_staff = True
        elif not self.is_superuser:
            self.is_staff = False

        if not self.requires_approval:
            self.approval_status = "approved"
            self.vendor_license_document_status = "not_required"
            self.pharmacist_registration_document_status = "not_required"
        elif self.role == "vendor":
            self.vendor_license_document_status = "pending" if self.vendor_license_document and self.vendor_license_document_status == "not_required" else self.vendor_license_document_status
            self.pharmacist_registration_document_status = "not_required"
        elif self.role == "pharmacist":
            self.pharmacist_registration_document_status = (
                "pending" if self.pharmacist_registration_document and self.pharmacist_registration_document_status == "not_required" else self.pharmacist_registration_document_status
            )
            self.vendor_license_document_status = "not_required"

        if self.requires_approval and self.approval_status == "pending" and self.approval_due_at is None:
            self.approval_due_at = timezone.now() + timezone.timedelta(hours=getattr(settings, "APPROVAL_REVIEW_SLA_HOURS", 24))

        if self.account_status == "deleted" and self.deleted_at is None:
            self.deleted_at = timezone.now()

        if self.account_status == "active" and not self.account_locked and self.deleted_at is None:
            self.is_active = True
        else:
            self.is_active = False

        super().save(*args, **kwargs)


class CustomerAddress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(max_length=80)
    recipient = models.CharField(max_length=255)
    line1 = models.CharField(max_length=255)
    district = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=120)
    state = models.CharField(max_length=120, blank=True)
    country = models.CharField(max_length=120, blank=True)
    pincode = models.CharField(max_length=20)
    phone_number = models.CharField(max_length=20, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "-updated_at"]

    def __str__(self) -> str:
        return f"{self.user} - {self.label}"


class CustomerWebsiteActivityDaily(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="website_activity_days")
    activity_date = models.DateField(db_index=True)
    active_seconds = models.PositiveIntegerField(default=0)
    heartbeat_count = models.PositiveIntegerField(default=0)
    last_heartbeat_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-activity_date"]
        constraints = [
            models.UniqueConstraint(fields=["user", "activity_date"], name="unique_customer_website_activity_day"),
        ]
        indexes = [
            models.Index(fields=["activity_date", "active_seconds"]),
            models.Index(fields=["user", "activity_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} - {self.activity_date}: {format_active_duration(self.active_seconds)}"


class SavedPaymentMethod(models.Model):
    METHOD_CHOICES = (
        ("UPI", "UPI"),
        ("CARD", "Card"),
        ("WALLET", "Wallet"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payment_methods")
    method_type = models.CharField(max_length=12, choices=METHOD_CHOICES)
    label = models.CharField(max_length=120)
    upi_id = models.CharField(max_length=120, blank=True)
    masked_details = models.CharField(max_length=120, blank=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "-updated_at"]

    def __str__(self) -> str:
        return f"{self.user} - {self.label}"


class OTPRequest(models.Model):
    PURPOSE_CHOICES = (
        ("login", "Login"),
        ("signup", "Signup"),
        ("reset", "Reset Password"),
    )

    phone_number = models.CharField(max_length=20, db_index=True)
    purpose = models.CharField(max_length=16, choices=PURPOSE_CHOICES, default="login")
    otp_code = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(blank=True, null=True)
    attempt_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["phone_number", "purpose", "created_at"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.phone_number} ({self.purpose})"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @classmethod
    def default_expiry(cls):
        return timezone.now() + timedelta(minutes=10)


class UserSavedFilterView(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_filter_views")
    name = models.CharField(max_length=120)
    filters = models.JSONField(default=dict, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        unique_together = [("owner", "name")]

    def __str__(self) -> str:
        return f"{self.owner} - {self.name}"


class RolePermissionMatrix(models.Model):
    ROLE_CHOICES = User.ROLE_CHOICES

    role = models.CharField(max_length=32, choices=ROLE_CHOICES, unique=True)
    matrix_permissions = models.JSONField(default=dict, blank=True)
    user_create = models.BooleanField(default=False)
    user_read = models.BooleanField(default=True)
    user_update = models.BooleanField(default=False)
    user_delete = models.BooleanField(default=False)
    user_lock = models.BooleanField(default=False)
    user_unlock = models.BooleanField(default=False)
    user_export = models.BooleanField(default=False)
    user_reset_password = models.BooleanField(default=False)
    user_audit_view = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["role"]

    def __str__(self) -> str:
        return self.get_role_display()
