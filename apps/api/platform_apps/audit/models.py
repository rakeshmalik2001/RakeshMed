from pathlib import Path

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    SEVERITY_CHOICES = (
        ("info", "Info"),
        ("warning", "Warning"),
        ("critical", "Critical"),
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    actor_label = models.CharField(max_length=160, blank=True)
    event_type = models.CharField(max_length=64)
    entity_type = models.CharField(max_length=64)
    entity_id = models.CharField(max_length=64, blank=True)
    severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES, default="info")
    message = models.CharField(max_length=255)
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type}: {self.message}"


class ManagedFile(models.Model):
    CATEGORY_CHOICES = (
        ("report", "Report"),
        ("prescription", "Prescription"),
        ("invoice", "Invoice"),
        ("compliance", "Compliance"),
        ("export", "Export"),
        ("other", "Other"),
    )
    VISIBILITY_CHOICES = (
        ("admin", "Admin"),
        ("ops", "Ops"),
        ("all_staff", "All Staff"),
    )

    title = models.CharField(max_length=160)
    category = models.CharField(max_length=24, choices=CATEGORY_CHOICES, default="other")
    file = models.FileField(upload_to="backoffice/%Y/%m/%d")
    description = models.TextField(blank=True)
    visibility = models.CharField(max_length=24, choices=VISIBILITY_CHOICES, default="all_staff")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="managed_files",
    )
    file_size_bytes = models.PositiveBigIntegerField(default=0)
    download_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title

    @property
    def filename(self) -> str:
        return Path(self.file.name).name

