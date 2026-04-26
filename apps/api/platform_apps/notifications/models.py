from django.conf import settings
from django.db import models


class Notification(models.Model):
    KIND_CHOICES = (
        ("order_update", "Order Update"),
        ("payment_update", "Payment Update"),
        ("prescription_update", "Prescription Update"),
        ("inventory_alert", "Inventory Alert"),
        ("system_alert", "System Alert"),
        ("account", "Account"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=32, choices=KIND_CHOICES, default="account")
    title = models.CharField(max_length=160)
    body = models.TextField()
    link = models.CharField(max_length=255, blank=True)
    meta = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user.phone_number} - {self.title}"
