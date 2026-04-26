from django.conf import settings
from django.db import models


class Order(models.Model):
    STATUS_CHOICES = (
        ("placed", "Placed"),
        ("pending_prescription_review", "Pending Prescription Review"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
    )
    PAYMENT_METHOD_CHOICES = (
        ("UPI", "UPI"),
        ("CARD", "Card"),
        ("COD", "Cash on Delivery"),
        ("WALLET", "Wallet"),
    )
    PAYMENT_STATUS_CHOICES = (
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("refund_pending", "Refund Pending"),
        ("refunded", "Refunded"),
        ("cod_pending", "Cash on Delivery Pending"),
    )
    INVENTORY_STATUS_CHOICES = (
        ("unreserved", "Unreserved"),
        ("reserved", "Reserved"),
        ("completed", "Completed"),
        ("released", "Released"),
        ("returned", "Returned"),
    )
    FULFILLMENT_STATUS_CHOICES = (
        ("queued", "Queued"),
        ("packed", "Packed"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("returned", "Returned"),
        ("cancelled", "Cancelled"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    order_number = models.CharField(max_length=32, unique=True)
    status = models.CharField(max_length=40, choices=STATUS_CHOICES, default="placed")
    payment_method = models.CharField(max_length=12, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending")
    inventory_status = models.CharField(max_length=20, choices=INVENTORY_STATUS_CHOICES, default="unreserved")
    fulfillment_status = models.CharField(max_length=20, choices=FULFILLMENT_STATUS_CHOICES, default="queued")
    tracking_reference = models.CharField(max_length=120, blank=True)
    address_label = models.CharField(max_length=120, blank=True)
    recipient = models.CharField(max_length=255)
    line1 = models.CharField(max_length=255)
    city = models.CharField(max_length=120)
    pincode = models.CharField(max_length=20)
    upi_id = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    requires_prescription_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.order_number


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "catalog.Product",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="order_items",
    )
    product_slug = models.SlugField(max_length=255)
    product_name = models.CharField(max_length=255)
    meta = models.CharField(max_length=255, blank=True)
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    qty = models.PositiveIntegerField(default=1)
    requires_prescription = models.BooleanField(default=False)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.order.order_number} - {self.product_name}"


class PaymentAttempt(models.Model):
    STATUS_CHOICES = (
        ("created", "Created"),
        ("pending", "Pending"),
        ("authorized", "Authorized"),
        ("captured", "Captured"),
        ("refunded", "Refunded"),
        ("failed", "Failed"),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payment_attempts")
    provider = models.CharField(max_length=40, default="simulated_gateway")
    payment_reference = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="created")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    raw_payload = models.JSONField(default=dict, blank=True)
    initiated_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-initiated_at"]

    def __str__(self) -> str:
        return f"{self.order.order_number} - {self.payment_reference}"


class OrderEvent(models.Model):
    EVENT_CHOICES = (
        ("placed", "Placed"),
        ("payment_session_started", "Payment Session Started"),
        ("payment_retry_started", "Payment Retry Started"),
        ("payment_captured", "Payment Captured"),
        ("payment_failed", "Payment Failed"),
        ("refund_requested", "Refund Requested"),
        ("refund_completed", "Refund Completed"),
        ("fulfillment_updated", "Fulfillment Updated"),
        ("cancelled", "Cancelled"),
        ("status_updated", "Status Updated"),
        ("payment_status_updated", "Payment Status Updated"),
        ("note_updated", "Note Updated"),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="timeline")
    event_type = models.CharField(max_length=40, choices=EVENT_CHOICES)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="order_events",
    )
    actor_label = models.CharField(max_length=120, blank=True)
    summary = models.CharField(max_length=255)
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.order.order_number} - {self.event_type}"


class RefundRequest(models.Model):
    STATUS_CHOICES = (
        ("requested", "Requested"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("processed", "Processed"),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="refund_requests")
    payment_attempt = models.ForeignKey(
        PaymentAttempt,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="refund_requests",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="refund_requests",
    )
    reason = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="requested")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    resolution_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.order.order_number} - {self.status}"


class PaymentWebhookEvent(models.Model):
    provider = models.CharField(max_length=40, default="simulated_gateway")
    event_id = models.CharField(max_length=120, unique=True)
    event_type = models.CharField(max_length=80)
    payment_reference = models.CharField(max_length=64, blank=True)
    order_number = models.CharField(max_length=32, blank=True)
    signature = models.CharField(max_length=255, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    was_duplicate = models.BooleanField(default=False)
    processed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.provider} - {self.event_id}"


class ReconciliationSnapshot(models.Model):
    provider = models.CharField(max_length=40, default="simulated_gateway")
    captured_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    refunded_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pending_refund_count = models.PositiveIntegerField(default=0)
    duplicate_webhooks = models.PositiveIntegerField(default=0)
    processed_webhooks = models.PositiveIntegerField(default=0)
    unmatched_paid_orders = models.PositiveIntegerField(default=0)
    created_by_label = models.CharField(max_length=120, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.provider} snapshot @ {self.created_at:%Y-%m-%d %H:%M:%S}"


class SettlementBatch(models.Model):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("processing", "Processing"),
        ("closed", "Closed"),
    )

    provider = models.CharField(max_length=40, default="simulated_gateway")
    batch_reference = models.CharField(max_length=64, unique=True)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    total_captured = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_refunded = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_net = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="draft")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="settlement_batches",
    )
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.batch_reference


class SettlementEntry(models.Model):
    STATUS_CHOICES = (
        ("settled", "Settled"),
        ("refunded", "Refunded"),
        ("netted", "Netted"),
    )

    settlement_batch = models.ForeignKey(SettlementBatch, on_delete=models.CASCADE, related_name="entries")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="settlement_entries")
    payment_attempt = models.ForeignKey(PaymentAttempt, on_delete=models.CASCADE, related_name="settlement_entries")
    refund_request = models.ForeignKey(
        RefundRequest,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="settlement_entries",
    )
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    settlement_status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="settled")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class Invoice(models.Model):
    STATUS_CHOICES = (
        ("issued", "Issued"),
        ("cancelled", "Cancelled"),
    )

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="invoice")
    invoice_number = models.CharField(max_length=40, unique=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="issued")
    recipient = models.CharField(max_length=255)
    line1 = models.CharField(max_length=255)
    city = models.CharField(max_length=120)
    pincode = models.CharField(max_length=20)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    snapshot = models.JSONField(default=dict, blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-issued_at"]

    def __str__(self) -> str:
        return self.invoice_number
