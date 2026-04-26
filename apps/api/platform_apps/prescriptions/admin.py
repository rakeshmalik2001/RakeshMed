from django.contrib import admin

from .models import Prescription, PrescriptionReview


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    save_on_top = True
    list_per_page = 25
    list_select_related = ("user", "reviewed_by")
    list_display = (
        "reference_code",
        "patient_name",
        "user",
        "status",
        "review_priority",
        "reviewed_by",
        "created_at",
    )
    list_filter = ("status", "review_priority", "reviewed_by")
    search_fields = ("reference_code", "patient_name", "doctor_name", "user__phone_number")
    readonly_fields = ("created_at", "updated_at", "reviewed_at")
    fieldsets = (
        ("Prescription Details", {"fields": ("reference_code", "user", "patient_name", "doctor_name")}),
        ("Upload", {"fields": ("uploaded_file_name", "uploaded_file_url", "uploaded_file_type", "storage_key", "uploaded_file_size_bytes")}),
        ("Review", {"fields": ("status", "review_priority", "review_eta_hours", "clarification_message", "reviewed_by", "reviewed_at")}),
        ("Notes", {"fields": ("notes",)}),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(PrescriptionReview)
class PrescriptionReviewAdmin(admin.ModelAdmin):
    save_on_top = True
    list_per_page = 25
    list_select_related = ("prescription", "reviewer")
    list_display = ("prescription", "reviewer", "decision", "created_at")
    list_filter = ("decision",)
    search_fields = ("prescription__reference_code", "reviewer__phone_number", "notes")
    readonly_fields = ("created_at",)
    fieldsets = (
        ("Review Decision", {"fields": ("prescription", "reviewer", "decision")}),
        ("Guidance", {"fields": ("notes", "substitute_guidance")}),
        ("Audit", {"fields": ("created_at",)}),
    )
