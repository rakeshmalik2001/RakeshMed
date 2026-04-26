from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import AuditLog, ManagedFile


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_per_page = 30
    list_display = ("created_at", "severity", "event_type", "entity_type", "actor_label", "message")
    list_filter = ("severity", "event_type", "entity_type")
    search_fields = ("actor_label", "message", "entity_id")
    readonly_fields = ("actor", "actor_label", "event_type", "entity_type", "entity_id", "severity", "message", "meta", "created_at")


@admin.register(ManagedFile)
class ManagedFileAdmin(admin.ModelAdmin):
    save_on_top = True
    list_per_page = 25
    list_display = ("title", "category", "visibility", "uploaded_by", "file_size_bytes", "download_count", "created_at", "download_link")
    list_filter = ("category", "visibility")
    search_fields = ("title", "description", "file")
    readonly_fields = ("file_size_bytes", "download_count", "created_at", "updated_at", "download_link")
    fieldsets = (
        ("File", {"fields": ("title", "category", "file", "description", "visibility", "uploaded_by")}),
        ("Telemetry", {"fields": ("file_size_bytes", "download_count", "download_link", "created_at", "updated_at")}),
    )

    def download_link(self, obj: ManagedFile):
        if not obj.pk:
            return "-"
        return format_html('<a href="{}">Download</a>', reverse("admin-managed-file-download", args=[obj.pk]))

    download_link.short_description = "Download"

