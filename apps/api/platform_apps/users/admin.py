from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone

from .models import CustomerAddress, OTPRequest, SavedPaymentMethod, User
from .services import notify_user_of_approval_decision


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    save_on_top = True
    list_per_page = 25
    ordering = ("email", "phone_number")
    actions = ("approve_selected_users", "reject_selected_users")
    list_display = ("email", "phone_number", "full_name", "role", "approval_specialty", "approval_available_for_assignment", "approval_unavailable_until", "approval_shift_start_hour", "approval_shift_end_hour", "approval_leave_dates", "account_status", "approval_status", "approval_assigned_to", "approval_due_at", "approval_last_escalated_at", "vendor_license_document_status", "pharmacist_registration_document_status", "approval_reviewed_at", "is_phone_verified", "is_active", "is_staff")
    list_filter = ("role", "approval_specialty", "approval_available_for_assignment", "account_status", "approval_status", "approval_assigned_to", "vendor_license_document_status", "pharmacist_registration_document_status", "is_phone_verified", "is_active", "is_staff")
    search_fields = ("email", "phone_number", "full_name")
    readonly_fields = ("created_at", "updated_at", "last_login", "approval_assigned_at", "approval_last_escalated_at", "approval_reviewed_at", "approval_reviewed_by")
    fieldsets = (
        ("Identity", {"fields": ("email", "phone_number", "full_name", "role", "business_name")}),
        ("Compliance", {"fields": ("vendor_license_number", "vendor_license_document", "vendor_license_document_status", "pharmacist_registration_number", "pharmacist_registration_document", "pharmacist_registration_document_status")}),
        ("Access", {"fields": ("account_status", "approval_status", "approval_specialty", "approval_available_for_assignment", "approval_unavailable_until", "approval_shift_start_hour", "approval_shift_end_hour", "approval_shift_weekdays", "approval_leave_dates", "approval_notes", "approval_assigned_to", "approval_assigned_at", "approval_due_at", "approval_last_escalated_at", "approval_reviewed_at", "approval_reviewed_by", "is_phone_verified", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Credentials", {"fields": ("password",)}),
        ("Audit", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "phone_number", "full_name", "role", "business_name", "vendor_license_number", "vendor_license_document", "vendor_license_document_status", "pharmacist_registration_number", "pharmacist_registration_document", "pharmacist_registration_document_status", "account_status", "approval_status", "approval_specialty", "approval_available_for_assignment", "approval_unavailable_until", "approval_shift_start_hour", "approval_shift_end_hour", "approval_shift_weekdays", "approval_leave_dates", "approval_notes", "approval_assigned_to", "approval_due_at", "password1", "password2", "is_staff", "is_superuser"),
            },
        ),
    )
    filter_horizontal = ("groups", "user_permissions")

    def save_model(self, request, obj, form, change):
        previous_status = None
        if change and obj.pk:
            previous_status = User.objects.get(pk=obj.pk).approval_status
        if obj.approval_status in {"approved", "rejected"}:
            obj.approval_reviewed_by = request.user
            obj.approval_reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)
        if previous_status is not None and previous_status != obj.approval_status:
            notify_user_of_approval_decision(obj, previous_status=previous_status, actor=request.user)

    @admin.action(description="Approve selected users")
    def approve_selected_users(self, request, queryset):
        updated = 0
        for user in queryset:
            previous_status = user.approval_status
            if previous_status == "approved":
                continue
            user.approval_status = "approved"
            user.approval_reviewed_by = request.user
            user.approval_reviewed_at = timezone.now()
            user.save(update_fields=["approval_status", "approval_reviewed_by", "approval_reviewed_at", "updated_at"])
            notify_user_of_approval_decision(user, previous_status=previous_status, actor=request.user)
            updated += 1
        self.message_user(request, f"{updated} user(s) approved.")

    @admin.action(description="Reject selected users")
    def reject_selected_users(self, request, queryset):
        updated = 0
        for user in queryset:
            previous_status = user.approval_status
            if previous_status == "rejected":
                continue
            user.approval_status = "rejected"
            user.approval_reviewed_by = request.user
            user.approval_reviewed_at = timezone.now()
            user.save(update_fields=["approval_status", "approval_reviewed_by", "approval_reviewed_at", "updated_at"])
            notify_user_of_approval_decision(user, previous_status=previous_status, actor=request.user)
            updated += 1
        self.message_user(request, f"{updated} user(s) rejected.")


@admin.register(OTPRequest)
class OTPRequestAdmin(admin.ModelAdmin):
    list_per_page = 25
    list_display = ("phone_number", "purpose", "otp_code", "expires_at", "verified_at", "created_at")
    list_filter = ("purpose", "verified_at")
    search_fields = ("phone_number", "otp_code")
    readonly_fields = ("created_at",)
    fieldsets = (
        ("OTP Details", {"fields": ("phone_number", "purpose", "otp_code", "attempt_count")}),
        ("Verification", {"fields": ("expires_at", "verified_at")}),
        ("Audit", {"fields": ("created_at",)}),
    )


@admin.register(CustomerAddress)
class CustomerAddressAdmin(admin.ModelAdmin):
    save_on_top = True
    list_per_page = 25
    list_select_related = ("user",)
    list_display = ("user", "label", "recipient", "city", "pincode", "is_default")
    list_filter = ("is_default", "city")
    search_fields = ("user__phone_number", "label", "recipient", "pincode")
    fieldsets = (
        ("Address Label", {"fields": ("user", "label", "is_default")}),
        ("Delivery Details", {"fields": ("recipient", "phone_number", "line1", "city", "state", "pincode")}),
    )


@admin.register(SavedPaymentMethod)
class SavedPaymentMethodAdmin(admin.ModelAdmin):
    save_on_top = True
    list_per_page = 25
    list_select_related = ("user",)
    list_display = ("user", "method_type", "label", "upi_id", "masked_details", "is_default", "is_active")
    list_filter = ("method_type", "is_default", "is_active")
    search_fields = ("user__phone_number", "label", "upi_id", "masked_details")
    fieldsets = (
        ("Method Details", {"fields": ("user", "method_type", "label")}),
        ("Identifiers", {"fields": ("upi_id", "masked_details")}),
        ("Status", {"fields": ("is_default", "is_active")}),
    )
