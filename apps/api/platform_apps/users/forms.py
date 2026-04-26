from __future__ import annotations

from pathlib import Path

from django import forms
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .access import PUBLIC_REGISTRATION_ROLES
from .location_catalog import get_all_countries, get_all_states, get_districts_of_state, get_states_of_country
from .models import CustomerAddress, User
from .role_catalog import ENTERPRISE_ROLE_CATALOG, get_role_catalog_entry


def _cache_key_for(identifier: str, ip_address: str) -> str:
    return f"portal-login-attempts:{identifier.lower()}:{ip_address}"


def _safe_cache_get(key: str, default=0):
    try:
        return cache.get(key, default)
    except Exception:
        return default


def _safe_cache_set(key: str, value, timeout: int):
    try:
        cache.set(key, value, timeout=timeout)
    except Exception:
        pass


def _safe_cache_delete(key: str):
    try:
        cache.delete(key)
    except Exception:
        pass


def _validate_approval_document(uploaded_file, *, field_label: str):
    if not uploaded_file:
        return

    max_size = int(getattr(settings, "APPROVAL_DOCUMENT_MAX_FILE_SIZE_BYTES", 5 * 1024 * 1024))
    allowed_extensions = {
        extension.lower()
        for extension in getattr(settings, "APPROVAL_DOCUMENT_ALLOWED_EXTENSIONS", [".pdf", ".jpg", ".jpeg", ".png"])
    }
    extension = Path(uploaded_file.name).suffix.lower()

    if extension not in allowed_extensions:
        raise ValidationError(f"{field_label} must be one of: {', '.join(sorted(allowed_extensions))}.")
    if uploaded_file.size > max_size:
        raise ValidationError(f"{field_label} must be {max_size // (1024 * 1024)}MB or smaller.")


class RegistrationForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    role = forms.ChoiceField(
        choices=[(role, User.ROLE_CHOICES_DICT[role]) for role in PUBLIC_REGISTRATION_ROLES]
        if hasattr(User, "ROLE_CHOICES_DICT")
        else [(role, dict(User.ROLE_CHOICES)[role]) for role in PUBLIC_REGISTRATION_ROLES]
    )

    class Meta:
        model = User
        fields = (
            "full_name",
            "email",
            "phone_number",
            "role",
            "business_name",
            "vendor_license_number",
            "vendor_license_document",
            "pharmacist_registration_number",
            "pharmacist_registration_document",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["full_name"].widget.attrs.update({"class": "form-control", "placeholder": "Full name"})
        self.fields["email"].widget.attrs.update({"class": "form-control", "placeholder": "name@example.com"})
        self.fields["phone_number"].widget.attrs.update({"class": "form-control", "placeholder": "9876543210"})
        self.fields["role"].widget.attrs.update({"class": "form-select"})
        self.fields["business_name"].widget.attrs.update({"class": "form-control", "placeholder": "Medical store or business name"})
        self.fields["vendor_license_number"].widget.attrs.update({"class": "form-control", "placeholder": "Drug license or store registration number"})
        self.fields["vendor_license_document"].widget.attrs.update({"class": "form-control"})
        self.fields["pharmacist_registration_number"].widget.attrs.update({"class": "form-control", "placeholder": "Pharmacist registration number"})
        self.fields["pharmacist_registration_document"].widget.attrs.update({"class": "form-control"})
        self.fields["password1"].widget.attrs.update({"class": "form-control", "placeholder": "Create password"})
        self.fields["password2"].widget.attrs.update({"class": "form-control", "placeholder": "Confirm password"})

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise ValidationError("Email address is required.")
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def clean_phone_number(self):
        phone_number = (self.cleaned_data.get("phone_number") or "").strip()
        if not phone_number:
            raise ValidationError("Phone number is required.")
        if User.objects.filter(phone_number=phone_number).exists():
            raise ValidationError("A user with this phone number already exists.")
        return phone_number

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        role = cleaned_data.get("role")
        business_name = (cleaned_data.get("business_name") or "").strip()
        vendor_license_number = (cleaned_data.get("vendor_license_number") or "").strip()
        vendor_license_document = cleaned_data.get("vendor_license_document")
        pharmacist_registration_number = (cleaned_data.get("pharmacist_registration_number") or "").strip()
        pharmacist_registration_document = cleaned_data.get("pharmacist_registration_document")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Passwords do not match.")
        if role == "vendor":
            if not business_name:
                self.add_error("business_name", "Business name is required for vendor registration.")
            if not vendor_license_number:
                self.add_error("vendor_license_number", "License or store registration number is required for vendor registration.")
            if not vendor_license_document:
                self.add_error("vendor_license_document", "Vendor proof document is required.")
            else:
                try:
                    _validate_approval_document(vendor_license_document, field_label="Vendor proof document")
                except ValidationError as exc:
                    self.add_error("vendor_license_document", exc)
        if role == "pharmacist":
            if not pharmacist_registration_number:
                self.add_error("pharmacist_registration_number", "Pharmacist registration number is required.")
            if not pharmacist_registration_document:
                self.add_error("pharmacist_registration_document", "Pharmacist proof document is required.")
            else:
                try:
                    _validate_approval_document(pharmacist_registration_document, field_label="Pharmacist proof document")
                except ValidationError as exc:
                    self.add_error("pharmacist_registration_document", exc)
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.account_status = "active"
        user.approval_status = "pending" if user.requires_approval else "approved"
        user.is_active = True
        user.email_verified = False
        user.set_password(self.cleaned_data["password1"])
        user.password_last_changed_at = timezone.now()
        if commit:
            user.save()
            if not user.created_by_id:
                user.created_by = user
            if not user.updated_by_id:
                user.updated_by = user
            if user.created_by_id == user.pk or user.updated_by_id == user.pk:
                user.save(update_fields=["created_by", "updated_by", "updated_at"])
        return user


class LoginForm(forms.Form):
    email = forms.CharField(widget=forms.TextInput(attrs={"autocomplete": "username"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))

    error_messages = {
        "invalid_login": "Please enter a valid email and password.",
        "blocked": "Your account is blocked. Please contact support.",
        "suspended": "Your account is suspended. Please contact support.",
        "inactive": "Your account is inactive.",
        "pending_approval": "Your account is awaiting admin approval.",
        "rejected": "Your account approval request was rejected.",
        "rate_limited": "Too many login attempts. Please try again later.",
    }

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.update({"class": "form-control", "placeholder": "Email or phone number"})
        self.fields["password"].widget.attrs.update({"class": "form-control", "placeholder": "Password"})

    def clean(self):
        cleaned_data = super().clean()
        email = (cleaned_data.get("email") or "").strip().lower()
        password = cleaned_data.get("password")
        ip_address = self._get_ip_address()
        key = _cache_key_for(email or "unknown", ip_address)
        max_attempts = int(getattr(settings, "LOGIN_THROTTLE_FAILURE_LIMIT", 5))

        if _safe_cache_get(key, 0) >= max_attempts:
            raise ValidationError(self.error_messages["rate_limited"])

        if email and password:
            matched_user = User.objects.filter(
                Q(email__iexact=email) | Q(phone_number=email) | Q(username__iexact=email)
            ).first()
            if matched_user:
                if matched_user.account_status == "blocked":
                    raise ValidationError(self.error_messages["blocked"])
                if matched_user.account_status == "suspended":
                    raise ValidationError(self.error_messages["suspended"])
                if matched_user.account_status == "inactive":
                    raise ValidationError(self.error_messages["inactive"])
                if matched_user.account_locked:
                    raise ValidationError("This account is locked. Please contact support.")
                if matched_user.approval_status == "pending":
                    raise ValidationError(self.error_messages["pending_approval"])
                if matched_user.approval_status == "rejected":
                    raise ValidationError(self.error_messages["rejected"])
                if not matched_user.is_active:
                    raise ValidationError(self.error_messages["inactive"])

            self.user_cache = authenticate(self.request, username=email, password=password, email=email)
            if self.user_cache is None:
                if matched_user:
                    matched_user.failed_login_attempts = (matched_user.failed_login_attempts or 0) + 1
                    if matched_user.failed_login_attempts >= max_attempts:
                        matched_user.account_locked = True
                    matched_user.save(update_fields=["failed_login_attempts", "account_locked", "updated_at"])
                _safe_cache_set(
                    key,
                    _safe_cache_get(key, 0) + 1,
                    timeout=int(getattr(settings, "LOGIN_THROTTLE_WINDOW_SECONDS", 900)),
                )
                raise ValidationError(self.error_messages["invalid_login"])
            _safe_cache_delete(key)
        return cleaned_data

    def get_user(self):
        return self.user_cache

    def _get_ip_address(self) -> str:
        if self.request is None:
            return "unknown"
        forwarded_for = self.request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return self.request.META.get("REMOTE_ADDR", "unknown")


class MFAVerifyForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={"autocomplete": "one-time-code"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["code"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "Enter 6-digit verification code",
                "inputmode": "numeric",
                "pattern": "[0-9]*",
            }
        )

    def clean_code(self):
        code = (self.cleaned_data.get("code") or "").strip()
        if not code.isdigit():
            raise ValidationError("Verification code must contain 6 digits.")
        return code


class UniqueEmailPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.update({"class": "form-control", "placeholder": "name@example.com"})

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not User.objects.filter(email__iexact=email, is_active=True, approval_status="approved").exists():
            raise ValidationError("No active account was found with that email address.")
        return email


class SecurePortalPasswordSetForm(SetPasswordForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.fields["new_password1"].widget.attrs.update({"class": "form-control", "autocomplete": "new-password"})
        self.fields["new_password2"].widget.attrs.update({"class": "form-control", "autocomplete": "new-password"})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.password_last_changed_at = timezone.now()
        user.force_password_reset = False
        if commit:
            user.save(update_fields=["password", "password_last_changed_at", "force_password_reset", "updated_at"])
        return user


class UserManagementForm(forms.ModelForm):
    country = forms.ChoiceField(required=True)
    state = forms.ChoiceField(required=False)
    district = forms.ChoiceField(required=False)
    department = forms.ChoiceField(required=True)
    designation = forms.ChoiceField(required=True)
    temporary_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Set a temporary password now, or enable invite-only onboarding below.",
    )
    invite_user = forms.BooleanField(
        required=False,
        help_text="Create the account without a usable password and mark it for onboarding/reset.",
    )

    class Meta:
        model = User
        fields = (
            "employee_code",
            "username",
            "full_name",
            "type_of_user",
            "role",
            "department",
            "designation",
            "email",
            "phone_number",
            "country",
            "state",
            "district",
            "address",
            "account_status",
            "email_verified",
            "account_locked",
            "mfa_enabled",
            "remarks",
        )

    def __init__(self, *args, **kwargs):
        self.is_create = kwargs.pop("is_create", False)
        self.current_actor = kwargs.pop("current_actor", None)
        super().__init__(*args, **kwargs)
        self._configure_role_dependent_fields()
        self._configure_location_fields()
        self.fields["employee_code"].widget.attrs.update({"class": "form-control", "placeholder": "ADM-48392174"})
        self.fields["username"].widget.attrs.update({"class": "form-control", "placeholder": "firstname.lastname"})
        self.fields["full_name"].widget.attrs.update({"class": "form-control", "placeholder": "Full name"})
        self.fields["type_of_user"].widget.attrs.update({"class": "form-select"})
        self.fields["email"].widget.attrs.update({"class": "form-control", "placeholder": "name@example.com"})
        self.fields["phone_number"].widget.attrs.update({"class": "form-control", "placeholder": "9876543210"})
        self.fields["role"].widget.attrs.update({"class": "form-select"})
        self.fields["department"].widget.attrs.update({"class": "form-select"})
        self.fields["designation"].widget.attrs.update({"class": "form-select"})
        self.fields["country"].widget.attrs.update({"class": "form-control", "placeholder": "Country"})
        self.fields["country"].widget.attrs.update({"class": "form-select"})
        self.fields["state"].widget.attrs.update({"class": "form-select"})
        self.fields["district"].widget.attrs.update({"class": "form-select"})
        self.fields["address"].widget.attrs.update({"class": "form-control", "placeholder": "Address", "rows": 3})
        self.fields["account_status"].widget.attrs.update({"class": "form-select"})
        self.fields["email_verified"].widget.attrs.update({"class": "form-check-input"})
        self.fields["account_locked"].widget.attrs.update({"class": "form-check-input"})
        self.fields["mfa_enabled"].widget.attrs.update({"class": "form-check-input"})
        self.fields["remarks"].widget.attrs.update({"class": "form-control", "placeholder": "Operational notes", "rows": 3})
        self.fields["temporary_password"].widget.attrs.update({"class": "form-control", "placeholder": "Temporary password"})
        self.fields["invite_user"].widget.attrs.update({"class": "form-check-input"})

        self.fields["employee_code"].required = not self.is_create
        self.fields["username"].required = not self.is_create
        self.fields["full_name"].required = True
        self.fields["type_of_user"].required = False
        self.fields["department"].required = False
        self.fields["designation"].required = False
        self.fields["country"].required = True
        self.fields["state"].required = False
        self.fields["district"].required = False
        self.fields["address"].required = True
        self.fields["email_verified"].required = False
        self.fields["account_locked"].required = False
        self.fields["mfa_enabled"].required = False

        if self.instance and self.instance.pk:
            self.fields["temporary_password"].help_text = "Leave blank to keep the existing password unchanged."
            self.fields["employee_code"].help_text = "Edit mode: enter an employee code and press Enter to fetch an existing user."
        else:
            self.fields["employee_code"].widget.attrs["readonly"] = "readonly"
            self.fields["employee_code"].help_text = "Add mode: employee code is generated automatically when a role is selected."

    def _selected_role_value(self) -> str:
        if self.is_bound:
            return (self.data.get("role") or "").strip()
        if self.instance and self.instance.pk and self.instance.role:
            return (self.instance.role or "").strip()
        return (self.initial.get("role") or "").strip()

    def _resolve_catalog_entry(self):
        return get_role_catalog_entry(self._selected_role_value())

    def _configure_role_dependent_fields(self) -> None:
        role_entry = self._resolve_catalog_entry()
        department_initial = ""
        designation_initial = ""
        if self.is_bound:
            department_initial = (self.data.get("department") or "").strip()
            designation_initial = (self.data.get("designation") or "").strip()
        elif self.instance and self.instance.pk:
            department_initial = (self.instance.department or "").strip()
            designation_initial = (self.instance.designation or "").strip()
        else:
            department_initial = (self.initial.get("department") or "").strip()
            designation_initial = (self.initial.get("designation") or "").strip()

        department_options = []
        designation_options = []
        for entry in ENTERPRISE_ROLE_CATALOG:
            if entry["department"] not in department_options:
                department_options.append(entry["department"])
            if entry["designation"] not in designation_options:
                designation_options.append(entry["designation"])
        if department_initial and department_initial not in department_options:
            department_options.append(department_initial)
        if designation_initial and designation_initial not in designation_options:
            designation_options.append(designation_initial)

        self.fields["department"].choices = [("", "Select department")] + [(value, value) for value in department_options]
        self.fields["designation"].choices = [("", "Select designation")] + [(value, value) for value in designation_options]
        self.fields["department"].initial = department_initial or (role_entry["department"] if role_entry else "")
        self.fields["designation"].initial = designation_initial or (role_entry["designation"] if role_entry else "")

    def _configure_location_fields(self) -> None:
        country_initial = ""
        state_initial = ""
        district_initial = ""
        if self.is_bound:
            country_initial = (self.data.get("country") or "").strip()
            state_initial = (self.data.get("state") or "").strip()
            district_initial = (self.data.get("district") or "").strip()
        elif self.instance and self.instance.pk:
            country_initial = (self.instance.country or "").strip()
            state_initial = (self.instance.state or "").strip()
            district_initial = (self.instance.district or "").strip()
        else:
            country_initial = (self.initial.get("country") or "").strip()
            state_initial = (self.initial.get("state") or "").strip()
            district_initial = (self.initial.get("district") or "").strip()

        country_choices = [("", "Select country")] + [(entry["name"], entry["name"]) for entry in get_all_countries()]
        state_options = get_all_states()
        district_options = get_districts_of_state(country_initial, state_initial)
        if country_initial:
            country_specific_states = get_states_of_country(country_initial)
            if country_specific_states:
                state_options = country_specific_states
        if state_initial and state_initial not in state_options:
            state_options.append(state_initial)
        if district_initial and district_initial not in district_options:
            district_options.append(district_initial)

        self.fields["country"].choices = country_choices
        self.fields["state"].choices = [("", "Select state")] + [(value, value) for value in state_options]
        self.fields["district"].choices = [("", "Select district")] + [(value, value) for value in district_options]
        self.fields["country"].initial = country_initial
        self.fields["state"].initial = state_initial
        self.fields["district"].initial = district_initial

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise ValidationError("Email is required.")
        qs = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def clean_phone_number(self):
        phone_number = (self.cleaned_data.get("phone_number") or "").strip()
        if not phone_number:
            raise ValidationError("Phone number is required.")
        if not phone_number.isdigit() or not 10 <= len(phone_number) <= 15:
            raise ValidationError("Phone number must contain 10 to 15 digits.")
        qs = User.objects.filter(phone_number=phone_number)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A user with this phone number already exists.")
        return phone_number

    def clean_country(self):
        country = (self.cleaned_data.get("country") or "").strip()
        if not country:
            raise ValidationError("Country is required.")
        return country

    def clean_state(self):
        state = (self.cleaned_data.get("state") or "").strip()
        country = (self.data.get("country") or self.cleaned_data.get("country") or "").strip()
        available_states = get_states_of_country(country)
        if available_states and not state:
            raise ValidationError("State is required.")
        return state

    def clean_district(self):
        district = (self.cleaned_data.get("district") or "").strip()
        country = (self.data.get("country") or self.cleaned_data.get("country") or "").strip()
        state = (self.data.get("state") or self.cleaned_data.get("state") or "").strip()
        available_districts = get_districts_of_state(country, state)
        if available_districts and not district:
            raise ValidationError("District is required.")
        return district

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip().lower()
        if self.is_create and not username:
            generated_username = User.generate_unique_username(
                (self.cleaned_data.get("full_name") or self.data.get("full_name") or ""),
                (self.cleaned_data.get("email") or self.data.get("email") or ""),
                (self.cleaned_data.get("phone_number") or self.data.get("phone_number") or ""),
            )
            return generated_username
        if not username:
            raise ValidationError("Username is required.")
        qs = User.objects.filter(username__iexact=username)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A user with this username already exists.")
        return username

    def clean_employee_code(self):
        employee_code = (self.cleaned_data.get("employee_code") or "").strip().upper()
        if self.is_create and not employee_code:
            role = (self.data.get("role") or self.cleaned_data.get("role") or "").strip()
            if not role:
                raise ValidationError("Select a role to generate an employee code.")
            return User.generate_unique_employee_code(role)
        if not employee_code:
            raise ValidationError("Employee code is required.")
        qs = User.objects.filter(employee_code__iexact=employee_code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A user with this employee code already exists.")
        return employee_code

    def clean_department(self):
        department = (self.cleaned_data.get("department") or "").strip()
        role_entry = self._resolve_catalog_entry()
        if role_entry:
            return role_entry["department"]
        if not department:
            raise ValidationError("Department is required.")
        return department

    def clean_designation(self):
        designation = (self.cleaned_data.get("designation") or "").strip()
        role_entry = self._resolve_catalog_entry()
        if role_entry:
            return role_entry["designation"]
        if not designation:
            raise ValidationError("Designation is required.")
        return designation

    def clean(self):
        cleaned_data = super().clean()
        temporary_password = (cleaned_data.get("temporary_password") or "").strip()
        invite_user = bool(cleaned_data.get("invite_user"))
        role_entry = get_role_catalog_entry(cleaned_data.get("role"))
        if role_entry:
            cleaned_data["type_of_user"] = role_entry["type_of_user_value"]
            cleaned_data["department"] = role_entry["department"]
            cleaned_data["designation"] = role_entry["designation"]
        if self.is_create and not temporary_password and not invite_user:
            self.add_error("temporary_password", "Provide a temporary password or choose invite user.")
        if temporary_password and len(temporary_password) < 8:
            self.add_error("temporary_password", "Temporary password must be at least 8 characters long.")
        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.phone_number = self.cleaned_data["phone_number"]
        user.username = self.cleaned_data["username"]
        user.employee_code = self.cleaned_data["employee_code"]
        user.country = self.cleaned_data["country"]
        user.state = self.cleaned_data["state"]
        user.district = self.cleaned_data["district"]
        user.address = self.cleaned_data["address"]
        user.force_password_reset = bool(self.cleaned_data.get("invite_user")) or bool(self.cleaned_data.get("temporary_password"))

        password = (self.cleaned_data.get("temporary_password") or "").strip()
        if password:
            user.set_password(password)
            user.password_last_changed_at = timezone.now()
        elif self.is_create and self.cleaned_data.get("invite_user"):
            user.set_unusable_password()
        elif self.is_create:
            user.set_unusable_password()
        if commit:
            if self.is_create and not user.created_by_id and self.current_actor:
                user.created_by = self.current_actor
            if self.current_actor:
                user.updated_by = self.current_actor
            if self.is_create and not user.employee_code:
                user.employee_code = User.generate_unique_employee_code(user.role)
            try:
                user.save()
            except IntegrityError:
                if not self.is_create:
                    raise
                user.employee_code = User.generate_unique_employee_code(user.role)
                user.save()
            existing_address = user.addresses.order_by("-is_default", "-updated_at").first()
            if existing_address is None:
                existing_address = CustomerAddress(user=user, label="Primary", recipient=user.full_name or user.phone_number, city=user.district or "")
            existing_address.recipient = user.full_name or user.phone_number
            existing_address.line1 = user.address
            existing_address.state = user.state
            existing_address.district = user.district
            existing_address.country = user.country
            existing_address.city = user.district or existing_address.city or "N/A"
            existing_address.phone_number = user.phone_number
            if not existing_address.pincode:
                existing_address.pincode = "000000"
            existing_address.is_default = True
            existing_address.save()
        return user
