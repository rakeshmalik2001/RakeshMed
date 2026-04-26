from django.utils import timezone
from django.db import IntegrityError
from rest_framework import serializers

from .models import CustomerAddress, OTPRequest, RolePermissionMatrix, SavedPaymentMethod, User, UserSavedFilterView


class UserSerializer(serializers.ModelSerializer):
    session_expires_at = serializers.SerializerMethodField()
    dashboard_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "phone_number",
            "email",
            "full_name",
            "role",
            "account_status",
            "approval_status",
            "is_phone_verified",
            "session_expires_at",
            "dashboard_url",
        )

    def get_session_expires_at(self, _obj):
        return self.context.get("session_expires_at")

    def get_dashboard_url(self, obj):
        from .access import resolve_dashboard_url

        return resolve_dashboard_url(obj)


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("full_name", "email")


class CustomerAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerAddress
        fields = (
            "id",
            "label",
            "recipient",
            "line1",
            "city",
            "state",
            "pincode",
            "phone_number",
            "is_default",
        )


class SavedPaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedPaymentMethod
        fields = (
            "id",
            "method_type",
            "label",
            "upi_id",
            "masked_details",
            "is_default",
            "is_active",
        )

    def validate(self, attrs):
        method_type = attrs.get("method_type") or getattr(self.instance, "method_type", "")
        upi_id = attrs.get("upi_id") or getattr(self.instance, "upi_id", "")
        masked_details = attrs.get("masked_details") or getattr(self.instance, "masked_details", "")

        if method_type == "UPI" and not upi_id:
            raise serializers.ValidationError({"upi_id": "UPI ID is required for UPI payment methods."})
        if method_type == "CARD" and not masked_details:
            raise serializers.ValidationError({"masked_details": "Masked card details are required for card methods."})
        return attrs


class SendOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    purpose = serializers.ChoiceField(choices=OTPRequest.PURPOSE_CHOICES, default="login")


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    otp_code = serializers.CharField(max_length=6, min_length=6)
    purpose = serializers.ChoiceField(choices=OTPRequest.PURPOSE_CHOICES, default="login")
    full_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)


class AdminUserManagementSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()
    password_expired = serializers.ReadOnlyField()
    customer_active_hrs_label = serializers.CharField(source="customer_active_duration_label", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
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
            "customer_active_seconds_total",
            "customer_active_hrs_label",
            "account_status",
            "email_verified",
            "account_locked",
            "mfa_enabled",
            "force_password_reset",
            "failed_login_attempts",
            "last_login",
            "last_login_ip",
            "password_last_changed_at",
            "password_expired",
            "created_at",
            "created_by",
            "created_by_name",
            "updated_at",
            "updated_by",
            "updated_by_name",
            "remarks",
        )
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by", "customer_active_seconds_total", "customer_active_hrs_label")

    def validate_email(self, value):
        email = (value or "").strip().lower()
        qs = User.objects.filter(email__iexact=email)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate_username(self, value):
        username = (value or "").strip().lower()
        if not username and self.instance is None:
            return User.generate_unique_username(
                self.initial_data.get("full_name") or "",
                self.initial_data.get("email") or "",
                self.initial_data.get("phone_number") or "",
            )
        if not username:
            raise serializers.ValidationError("Username is required.")
        qs = User.objects.filter(username__iexact=username)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return username

    def validate_employee_code(self, value):
        employee_code = (value or "").strip().upper()
        if not employee_code and self.instance is None:
            role = (self.initial_data.get("role") or "").strip()
            if not role:
                raise serializers.ValidationError("Role is required to generate employee code.")
            return User.generate_unique_employee_code(role)
        qs = User.objects.filter(employee_code__iexact=employee_code)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A user with this employee code already exists.")
        return employee_code

    def validate_phone_number(self, value):
        phone_number = (value or "").strip()
        if not phone_number.isdigit() or not 10 <= len(phone_number) <= 15:
            raise serializers.ValidationError("Phone number must contain 10 to 15 digits.")
        qs = User.objects.filter(phone_number=phone_number)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return phone_number

    def create(self, validated_data):
        actor = self.context["request"].user
        temporary_password = self.context.get("temporary_password", "")
        invite_user = bool(self.context.get("invite_user"))
        if not validated_data.get("username"):
            validated_data["username"] = User.generate_unique_username(
                validated_data.get("full_name", ""),
                validated_data.get("email", ""),
                validated_data.get("phone_number", ""),
            )
        if not validated_data.get("employee_code"):
            validated_data["employee_code"] = User.generate_unique_employee_code(validated_data.get("role", ""))
        user = User(**validated_data)
        user.created_by = actor
        user.updated_by = actor
        if temporary_password:
            user.set_password(temporary_password)
            user.password_last_changed_at = timezone.now()
            user.force_password_reset = True
        elif invite_user:
            user.set_unusable_password()
            user.force_password_reset = True
        else:
            user.set_unusable_password()
        try:
            user.save()
        except IntegrityError:
            user.employee_code = User.generate_unique_employee_code(user.role)
            user.save()
        return user

    def update(self, instance, validated_data):
        actor = self.context["request"].user
        for key, value in validated_data.items():
            setattr(instance, key, value)
        temporary_password = self.context.get("temporary_password", "")
        if temporary_password:
            instance.set_password(temporary_password)
            instance.password_last_changed_at = timezone.now()
            instance.force_password_reset = True
        instance.updated_by = actor
        instance.save()
        return instance

    def get_created_by_name(self, obj):
        if not obj.created_by:
            return ""
        return obj.created_by.full_name or obj.created_by.phone_number

    def get_updated_by_name(self, obj):
        if not obj.updated_by:
            return ""
        return obj.updated_by.full_name or obj.updated_by.phone_number


class UserSavedFilterViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSavedFilterView
        fields = ("id", "name", "filters", "is_default", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")


class RolePermissionMatrixSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolePermissionMatrix
        fields = (
            "id",
            "role",
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
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")
