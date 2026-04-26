from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    save_on_top = True
    list_per_page = 25
    list_select_related = ("user",)
    list_display = ("title", "user", "kind", "is_read", "created_at")
    list_filter = ("kind", "is_read")
    search_fields = ("title", "body", "user__phone_number", "user__full_name")
    readonly_fields = ("created_at", "read_at")
    fieldsets = (
        ("Notification", {"fields": ("user", "kind", "title", "body", "link")}),
        ("Metadata", {"fields": ("meta",)}),
        ("Read State", {"fields": ("is_read", "read_at")}),
        ("Audit", {"fields": ("created_at",)}),
    )
