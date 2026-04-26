from django.contrib import admin

from .models import (
    Invoice,
    Order,
    OrderEvent,
    OrderItem,
    PaymentAttempt,
    PaymentWebhookEvent,
    ReconciliationSnapshot,
    RefundRequest,
    SettlementBatch,
    SettlementEntry,
)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ("product_name", "product_slug", "qty", "sale_price", "requires_prescription")


class PaymentAttemptInline(admin.TabularInline):
    model = PaymentAttempt
    extra = 0
    readonly_fields = ("payment_reference", "provider", "status", "amount", "initiated_at", "confirmed_at")


class OrderEventInline(admin.TabularInline):
    model = OrderEvent
    extra = 0
    readonly_fields = ("event_type", "actor", "actor_label", "summary", "created_at")


class RefundRequestInline(admin.TabularInline):
    model = RefundRequest
    extra = 0
    readonly_fields = ("requested_by", "reason", "status", "amount", "created_at", "processed_at")


class InvoiceInline(admin.StackedInline):
    model = Invoice
    extra = 0
    readonly_fields = (
        "invoice_number",
        "status",
        "subtotal",
        "discount",
        "delivery_fee",
        "tax_amount",
        "total",
        "issued_at",
        "updated_at",
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    save_on_top = True
    list_per_page = 25
    list_select_related = ("user",)
    list_display = ("order_number", "user", "status", "payment_method", "total", "created_at")
    list_filter = ("status", "payment_method", "payment_status")
    search_fields = ("order_number", "user__phone_number", "recipient", "city", "pincode")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Order Summary", {"fields": ("order_number", "user", "status", "payment_method", "payment_status")}),
        ("Delivery", {"fields": ("address_label", "recipient", "line1", "city", "pincode")}),
        ("Payment", {"fields": ("upi_id", "subtotal", "discount", "delivery_fee", "total")}),
        ("Operational Notes", {"fields": ("requires_prescription_count", "notes")}),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )
    inlines = [OrderItemInline, PaymentAttemptInline, OrderEventInline, RefundRequestInline, InvoiceInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    save_on_top = True
    list_per_page = 25
    list_select_related = ("order", "product")
    list_display = ("order", "product_name", "qty", "requires_prescription")
    list_filter = ("requires_prescription",)
    search_fields = ("order__order_number", "product_name", "product_slug")
    fieldsets = (
        ("Order Item", {"fields": ("order", "product", "product_slug", "product_name", "meta")}),
        ("Pricing and Quantity", {"fields": ("mrp", "sale_price", "qty", "requires_prescription")}),
    )


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(admin.ModelAdmin):
    save_on_top = True
    list_per_page = 25
    list_select_related = ("order",)
    list_display = ("payment_reference", "order", "provider", "status", "amount", "initiated_at")
    list_filter = ("provider", "status")
    search_fields = ("payment_reference", "order__order_number", "order__recipient")
    readonly_fields = ("initiated_at", "confirmed_at")
    fieldsets = (
        ("Payment Attempt", {"fields": ("order", "provider", "payment_reference", "status", "amount")}),
        ("Payload", {"fields": ("raw_payload",)}),
        ("Audit", {"fields": ("initiated_at", "confirmed_at")}),
    )


@admin.register(OrderEvent)
class OrderEventAdmin(admin.ModelAdmin):
    save_on_top = True
    list_per_page = 25
    list_select_related = ("order", "actor")
    list_display = ("order", "event_type", "actor", "actor_label", "created_at")
    list_filter = ("event_type",)
    search_fields = ("order__order_number", "summary", "actor_label", "actor__phone_number")
    readonly_fields = ("created_at",)
    fieldsets = (
        ("Event", {"fields": ("order", "event_type", "actor", "actor_label", "summary")}),
        ("Metadata", {"fields": ("meta",)}),
        ("Audit", {"fields": ("created_at",)}),
    )


@admin.register(RefundRequest)
class RefundRequestAdmin(admin.ModelAdmin):
    save_on_top = True
    list_per_page = 25
    list_select_related = ("order", "payment_attempt", "requested_by")
    list_display = ("order", "status", "amount", "requested_by", "created_at", "processed_at")
    list_filter = ("status",)
    search_fields = ("order__order_number", "reason", "requested_by__phone_number", "requested_by__full_name")
    readonly_fields = ("created_at", "updated_at", "processed_at")
    fieldsets = (
        ("Refund Request", {"fields": ("order", "payment_attempt", "requested_by", "status", "amount")}),
        ("Reasoning", {"fields": ("reason", "resolution_notes")}),
        ("Audit", {"fields": ("created_at", "updated_at", "processed_at")}),
    )


@admin.register(PaymentWebhookEvent)
class PaymentWebhookEventAdmin(admin.ModelAdmin):
    save_on_top = True
    list_per_page = 25
    list_display = ("event_id", "provider", "event_type", "order_number", "payment_reference", "was_duplicate", "created_at")
    list_filter = ("provider", "event_type", "was_duplicate")
    search_fields = ("event_id", "order_number", "payment_reference")
    readonly_fields = ("created_at", "processed_at")
    fieldsets = (
        ("Webhook Event", {"fields": ("provider", "event_id", "event_type", "payment_reference", "order_number")}),
        ("Security and Flags", {"fields": ("signature", "was_duplicate")}),
        ("Payload", {"fields": ("payload",)}),
        ("Audit", {"fields": ("processed_at", "created_at")}),
    )


@admin.register(ReconciliationSnapshot)
class ReconciliationSnapshotAdmin(admin.ModelAdmin):
    save_on_top = True
    list_per_page = 25
    list_display = ("provider", "captured_total", "refunded_total", "created_by_label", "created_at")
    list_filter = ("provider",)
    search_fields = ("provider", "created_by_label", "notes")
    readonly_fields = ("created_at",)
    fieldsets = (
        ("Snapshot Summary", {"fields": ("provider", "captured_total", "refunded_total")}),
        ("Operational Counts", {"fields": ("pending_refund_count", "duplicate_webhooks", "processed_webhooks", "unmatched_paid_orders")}),
        ("Notes", {"fields": ("created_by_label", "notes")}),
        ("Audit", {"fields": ("created_at",)}),
    )


class SettlementEntryInline(admin.TabularInline):
    model = SettlementEntry
    extra = 0
    readonly_fields = ("order", "payment_attempt", "refund_request", "gross_amount", "refund_amount", "net_amount", "settlement_status")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    save_on_top = True
    list_per_page = 25
    list_select_related = ("order",)
    list_display = ("invoice_number", "order", "status", "total", "issued_at")
    list_filter = ("status", "issued_at")
    search_fields = ("invoice_number", "order__order_number", "recipient", "city", "pincode")
    readonly_fields = ("issued_at", "updated_at")
    fieldsets = (
        ("Invoice", {"fields": ("invoice_number", "order", "status")}),
        ("Customer", {"fields": ("recipient", "line1", "city", "pincode")}),
        ("Totals", {"fields": ("subtotal", "discount", "delivery_fee", "tax_amount", "total")}),
        ("Snapshot", {"fields": ("snapshot",)}),
        ("Audit", {"fields": ("issued_at", "updated_at")}),
    )


@admin.register(SettlementBatch)
class SettlementBatchAdmin(admin.ModelAdmin):
    save_on_top = True
    list_per_page = 25
    list_select_related = ("created_by",)
    list_display = ("batch_reference", "provider", "status", "total_captured", "total_refunded", "total_net", "created_at")
    list_filter = ("provider", "status")
    search_fields = ("batch_reference", "notes", "created_by__phone_number", "created_by__full_name")
    readonly_fields = ("created_at",)
    fieldsets = (
        ("Settlement Batch", {"fields": ("batch_reference", "provider", "status", "created_by")}),
        ("Period", {"fields": ("period_start", "period_end")}),
        ("Totals", {"fields": ("total_captured", "total_refunded", "total_net")}),
        ("Notes", {"fields": ("notes",)}),
        ("Audit", {"fields": ("created_at",)}),
    )
    inlines = [SettlementEntryInline]
