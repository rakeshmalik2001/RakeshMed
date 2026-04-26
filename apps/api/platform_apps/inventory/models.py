from django.conf import settings
from django.db import models


class StockLocation(models.Model):
    KIND_CHOICES = (
        ("warehouse", "Warehouse"),
        ("pharmacy", "Pharmacy"),
        ("returns", "Returns"),
        ("quarantine", "Quarantine"),
    )

    name = models.CharField(max_length=120)
    code = models.CharField(max_length=24, unique=True)
    kind = models.CharField(max_length=24, choices=KIND_CHOICES, default="warehouse")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class InventoryItem(models.Model):
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="inventory_items")
    location = models.ForeignKey(StockLocation, on_delete=models.CASCADE, related_name="inventory_items")
    quantity_on_hand = models.IntegerField(default=0)
    reserved_quantity = models.PositiveIntegerField(default=0)
    inbound_quantity = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["product__name", "location__sort_order", "location__name"]
        unique_together = ("product", "location")
        indexes = [
            models.Index(fields=["product", "location"]),
        ]

    @property
    def available_quantity(self) -> int:
        return self.quantity_on_hand - self.reserved_quantity

    def __str__(self) -> str:
        return f"{self.product} @ {self.location.code}"


class LowStockRule(models.Model):
    product = models.OneToOneField("catalog.Product", on_delete=models.CASCADE, related_name="low_stock_rule")
    threshold_quantity = models.PositiveIntegerField(default=5)
    location = models.ForeignKey(
        StockLocation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="low_stock_rules",
        help_text="Optional location-specific threshold. Leave empty to evaluate across all active locations.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["product__name"]

    def __str__(self) -> str:
        return f"{self.product} low stock <= {self.threshold_quantity}"


class StockMovement(models.Model):
    MOVEMENT_CHOICES = (
        ("restock", "Restock"),
        ("adjustment", "Adjustment"),
        ("sale_allocation", "Sale Allocation"),
        ("sale_release", "Sale Release"),
        ("sale_complete", "Sale Complete"),
        ("return", "Return"),
        ("damage", "Damage"),
        ("transfer_in", "Transfer In"),
        ("transfer_out", "Transfer Out"),
        ("manual_count", "Manual Count"),
    )

    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="stock_movements")
    inventory_item = models.ForeignKey(
        InventoryItem,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="movements",
    )
    location = models.ForeignKey(StockLocation, on_delete=models.PROTECT, related_name="movements")
    movement_type = models.CharField(max_length=24, choices=MOVEMENT_CHOICES, default="adjustment")
    quantity_delta = models.IntegerField()
    reference = models.CharField(max_length=120, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inventory_movements",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product", "created_at"]),
            models.Index(fields=["location", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.product} {self.quantity_delta:+} @ {self.location.code}"

