from django.conf import settings
from django.db import models


class DeliveryZone(models.Model):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=24, unique=True)
    pincode_prefix = models.CharField(max_length=6, db_index=True)
    city = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=120, blank=True)
    eta_min_hours = models.PositiveIntegerField(default=24)
    eta_max_hours = models.PositiveIntegerField(default=48)
    cod_available = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["pincode_prefix", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class DeliveryShipment(models.Model):
    STATUS_CHOICES = (
        ("queued", "Queued"),
        ("assigned", "Assigned"),
        ("picked_up", "Picked Up"),
        ("in_transit", "In Transit"),
        ("out_for_delivery", "Out for Delivery"),
        ("delivered", "Delivered"),
        ("failed", "Failed"),
        ("returned", "Returned"),
        ("cancelled", "Cancelled"),
    )
    SERVICE_LEVEL_CHOICES = (
        ("standard", "Standard"),
        ("express", "Express"),
    )

    order = models.OneToOneField("orders.Order", on_delete=models.CASCADE, related_name="delivery_shipment")
    zone = models.ForeignKey(
        DeliveryZone,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="shipments",
    )
    carrier_name = models.CharField(max_length=120, default="TrueCare Dispatch")
    service_level = models.CharField(max_length=20, choices=SERVICE_LEVEL_CHOICES, default="standard")
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="queued")
    tracking_reference = models.CharField(max_length=120, blank=True)
    status_notes = models.CharField(max_length=255, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    reattempt_count = models.PositiveIntegerField(default=0)
    eta_start = models.DateTimeField(null=True, blank=True)
    eta_end = models.DateTimeField(null=True, blank=True)
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["status", "updated_at"]),
            models.Index(fields=["tracking_reference"]),
        ]

    def __str__(self) -> str:
        return f"{self.order.order_number} - {self.status}"


class DeliveryEvent(models.Model):
    shipment = models.ForeignKey(DeliveryShipment, on_delete=models.CASCADE, related_name="events")
    status = models.CharField(max_length=24, choices=DeliveryShipment.STATUS_CHOICES)
    summary = models.CharField(max_length=255)
    meta = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="delivery_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.shipment.order.order_number} - {self.status}"
